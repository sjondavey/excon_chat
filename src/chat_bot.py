import logging
import pandas as pd
import openai
from collections import Counter
import os
import fnmatch
import regex # fuzzy lookup of references in a section of text

import importlib
import src.valid_index
importlib.reload(src.valid_index)
from src.valid_index import ValidIndex, get_excon_manual_index

import src.file_tools
importlib.reload(src.file_tools)
from src.file_tools import get_regulation_detail, \
                           num_tokens_from_string

import src.embeddings
importlib.reload(src.embeddings)
from src.embeddings import get_ada_embedding, \
                           get_closest_nodes

class ExconManual():
    def __init__(self, log_file = '', input_folder = "./inputs/"):
        # Set up basic configuration first
        if log_file == '':
            logging.basicConfig(level=logging.INFO)
        else: 
            logging.basicConfig(filename=log_file, filemode='w', format='%(name)s - %(levelname)s - %(message)s')
        
        # Then get the logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)  # Set level for the logger

        self.index_checker = get_excon_manual_index()
        self.df_excon = pd.read_csv(input_folder + "excon_processed_manual.csv", sep="|", encoding="utf-8", na_filter=False)  
        if self.df_excon.isna().any().any():
            raise ValueError(f'Encountered NaN values while loading {input_folder}excon_processed_manual.csv. This will cause ugly issues with the get_regulation_detail method')

        # Load the definitions. 
        definitions_and_embeddings_file = input_folder + "definitions.parquet"
        self.df_definitions_all = pd.read_parquet(definitions_and_embeddings_file, engine='pyarrow')
        
        # Load the section headings. 
        text_and_embeddings_file = input_folder + "text.parquet"
        self.df_text_all = pd.read_parquet(text_and_embeddings_file, engine='pyarrow')

        self.system_states = ["rag",                          # System is going to try RAG         
                              "no_relevant_embeddings",       # found embeddings but LLM doesn't think they help answer the question
                              "requires_additional_sections", # System asked for something but we could not identify it as a valid section OR a query to the text with this index returns null
                              "stuck"]                        # Terminal state. Once in this state no further progress can be made and user must restart
        self.system_state = self.system_states[0]

        
        self.messages = []
        self.reset_conversation_history()

        self.rag_prefixes = ["ANSWER:",  # LLM was able to answer the question with the input data
                             "SECTION:", # LLM Requested additional information to answer the question
                             "NONE:",    # The input data was not helpful
                             "FAIL:"]    # The LLM did not follow instructions

        self.assistant_msg_no_data = "I was unable to find any relevant documentation to assist in answering the question. Can you try re-phrasing the question?"
        self.assistant_msg_no_relevant_data = "The documentation I have been provided does not help me answer the question. Please re-phrase it and lets try again?"
        self.assistant_msg_stuck = "Unfortunately the system is in an unrecoverable state. Please restart the chat"
        self.assistant_msg_unknown_state = "The system is in an unknown state and cannot proceed. Please restart the chat"
        self.assistant_msg_llm_not_following_instructions = "The call to the LLM resulted in a response that did not fit parameters, even after retrying it. Please restart the chat and try phrasing the question differently"



    def reset_conversation_history(self):
        opening_message = "I am a bot designed to answer questions based on the Exchange Control Manual for Authorised Dealers. How can I assist today?"
        self.messages = [{"role": "assistant", "content": opening_message}]
        self.system_state = self.system_states[0]
        
    # Note: To test the workflow I need some way to control the openai API responses. I have chosen to do this with the two parameters
    #       testing: a flag. If false the function will run calling the openai api for responses. If false the function will 
    #                        select the response from the list of responses manual_responses_for_testing
    #       manual_responses_for_testing: A list of text. If testing == True, these values will be used as if they were the 
    #                                     the response from the API. This function can make multiple calls to the API so the i-th
    #                                     row in the list corresponds to the i-th call of the API
    #  
    def user_provides_input(self, user_context, threshold, model_to_use, temperature, max_tokens,
                            testing = False, manual_responses_for_testing = []):
        
        # I'm not sure I really understand how I should work with the Streamlit front end but I seem to need to add the 
        # user message in a step before I call "user_provides_input". This can result in the message being duplicated in the
        # list so here I include a "streamlit ui" check
        if not (self.messages[-1]["role"] == "user" and self.messages[-1]["content"] == user_context): 
            self.messages.append({"role": "user", "content": user_context})

        if self.system_state == self.system_states[3]: #stuck
            self.messages.append({"role": "assistant", "content": self.assistant_msg_stuck})
            return 
        elif self.system_state == self.system_states[0]: #"rag":
            self.logger.info("Entering RAG with query: " + user_context)
            df_definitions, df_search_sections = self.similarity_search(user_context, threshold)
            if len(df_definitions) + len(df_search_sections) == 0:
                self.logger.info("Unable to find any definitions or text related to this query")
                self.system_state = self.system_states[0] # "rag"
                self.messages.append({"role": "assistant", "content": self.assistant_msg_no_data})
                return
            else:
                flag, response = self.resource_augmented_query(model_to_use, temperature, max_tokens, df_definitions, df_search_sections,
                                                               testing, manual_responses_for_testing)
                if flag == self.rag_prefixes[0]: # "ANSWER:"
                    self.logger.info("-- Question asked and answered")
                    self.logger.info(f"\nAssistant: {response.strip()}")

                    self.messages.append({"role": "assistant", "content": response.strip()})
                    self.system_state = self.system_states[0] # RAG
                    return 
                elif flag == self.rag_prefixes[1]: # "SECTION:"
                    self.logger.info("Question asked. Request for more info")
                    df_search_sections = self.add_section_to_resource(modified_section_to_add, df_search_sections)
                    if self.system_state == self.system_states[2]: # "requires_additional_sections"
                        # TODO: Do you want to ask the user for help?
                        self.logger.info("Request to add resources failed")
                        self.system_state = self.system_states[3] # Stuck
                        self.messages.append({"role": "assistant", "content": self.assistant_msg_stuck}) 

                        raise NotImplementedError() # I need to work out out to proceed from here
                        #TODO: Perhaps separate out the two cases?
                        message = f"The system has requested an additional section in order to answer your query. \
                            It requested section {section_to_add} but this is either not a valid index or the index \
                            does not seem to exist in the data. If you are able to construct a valid index from the \
                                value {section_to_add} please input it now otherwise please restart the chat."
                        self.messages.append({"role": "assistant", "content": self.message})                        
                        return
                    # try again with new resources
                    flag, response = self.resource_augmented_query(model_to_use, temperature, max_tokens, df_definitions, df_search_sections,
                                                                   testing, manual_responses_for_testing)
                    if flag == self.rag_prefixes[0]: # "ANSWER:"
                        self.logger.info("Question answered with the additional information")
                        self.messages.append({"role": "assistant", "content": response.strip()})
                        self.system_state = self.system_states[0] # RAG
                        return
                    else: 
                        self.logger.info("Even with the additional information, they system was unable to answer the question. Placing the system in 'stuck' mode")
                        self.messages.append({"role": "assistant", "content": "A call for additional information to answer the question failed. The system is now stuck. Please restart it"})                        
                        self.system_state = self.system_states[3] # Stuck
                        return

                elif flag == self.rag_prefixes[2]: # "NONE:"
                    self.logger.info("The LLM was not able to find anything relevant in the supplied sections")
                    self.messages.append({"role": "assistant", "content": self.assistant_msg_no_relevant_data})
                    self.system_state = self.system_states[0] # RAG
                    return

                else:
                    self.logger.error("RAG returned an unexpected response")
                    self.messages.append({"role": "assistant", "content": self.assistant_msg_llm_not_following_instructions})
                    self.system_state = self.system_states[3] #stuck # We are at a dead end.
        else:
            self.logger.error("The system is in an unknown state")
            self.messages.append({"role": "assistant", "content": self.assistant_msg_unknown_state})

    def add_section_to_resource(self, section_to_add, df_search_sections):
        # Step 1) confirm it is requesting something that passes validation
        modified_section_to_add = self.index_checker.extract_valid_reference(section_to_add)
        if modified_section_to_add is None:
            self.system_state = self.system_states[2] # "requires_additional_sections"
            return df_search_sections
        try: # passes index verification but there is an error retrieving the section
            self.get_regulation_detail(modified_section_to_add)
        except Exception as e:
            self.system_state = self.system_states[2] # "requires_additional_sections"
            return df_search_sections
          
        referring_sections = self._find_reference_that_calls_for(modified_section_to_add, df_search_sections)
        
        if len(referring_sections) > 0: # Delete the other sections, keep the referring section and the new data
            referring_sections.append(modified_section_to_add)
            # now create the new RAG df_search_sections
            manual_data = []
            for i in range(len(referring_sections)):
                section = referring_sections[i]
                count = 1
                raw_text = self.get_regulation_detail(section)
                token_count = num_tokens_from_string(raw_text)
                manual_data.append([section, count, raw_text, token_count])            
            df_manual_data = pd.DataFrame(manual_data, columns = ["reference", "count", "raw_text", "token_count"])
            return df_manual_data
        else: # Just add the new data and hope the total context is not too long
            section = modified_section_to_add
            count = 1
            raw_text = self.get_regulation_detail(section)
            token_count = num_tokens_from_string(raw_text)
            df_search_sections.loc[len(df_search_sections.index)] = [section, count, raw_text, token_count]
            return df_search_sections


    # Note that 'section' is assumed to be valid at this stage
    def _find_reference_that_calls_for(self, valid_section_index, df_search_sections):
        referring_section = []
        if len(df_search_sections) == 1:
            referring_section.append(df_search_sections.iloc[0]["reference"])
        else:
            for index, row in df_search_sections.iterrows():
                match = self._find_fuzzy_reference(row["raw_text"], valid_section_index)
                if match:
                    referring_section.append(row["reference"])
        if len(referring_section) == 0:
            self.logger.error(f"The LLM asked for an additional valid reference {valid_section_index} but we could not determine which section referred to it")
        return referring_section
       

    # TODO: Think about replacing this with just the function ValidIndex.extract_valid_reference
    # I think that if we delete the first line of raw_text then we should be able to run ValidIndex.extract_valid_reference
    # on the remaining text to see if the valid_section_index was in the raw_section. It will get rid of some code and cater
    # also for cases with the reference in the raw_section is not correctly formatted rather than allowing for some random 
    # number of mismatches as I do here
    def _find_fuzzy_reference(self, raw_section, valid_section_index):
        # Enabling fuzzy matching with 2 insertions/deletions/substitutions to cater for stray spaces that may creep into the text
        pattern = r'(%s){e<=2}' % regex.escape(valid_section_index)
        match = regex.search(pattern, raw_section)
        if match:
            return match.group()
        else:
            return None

    # Make sure the last entry in self.messages is the user context
    # Note: To test the workflow I need some way to control the responses. I have chosen to do this with the two parameters
    #       testing: a flag. If false the function will run calling the openai api for responses. If false the function will 
    #                        select the response from the list of responses manual_responses_for_testing
    #       manual_responses_for_testing: A list of text. If testing == True, these values will be used as if they were the 
    #                                     the response from the API. This function can make multiple calls to the API so the i-th
    #                                     row in the list corresponds to the i-th call of the API
    #  
    def resource_augmented_query(self, model_to_use, temperature, max_tokens, df_definitions, df_search_sections,
                                 testing = False, manual_responses_for_testing = []):
        if len(self.messages) == 0 or self.messages[-1]["role"] != "user": 
            self.logger.error("resource_augmented_query method called but the last message on the stack was not from the user")
            self.system_state == self.system_states[3] # stuck
            return self.system_states[3], self.system_states[3]
        if self.system_state != "rag":
            self.logger.error("resource_augmented_query method called but the the system is not in rag state")
            self.system_state == self.system_states[3] # stuck
            return self.system_states[3], self.system_states[3]
        

        if len(df_definitions) + len(df_search_sections) > 0: # should always be the case as we check this in the control loop
            system_context = f"You are attempting to answer questions from an Authorised Dealer based only on the relevant documentation provided. You have only three options:\n\
1) Answer the question. If you do this, your must preface to response with the word '{self.rag_prefixes[0]}'. If possible also provide a reference to the relevant documentation for the user to cross-check. Use this if you are sure about your answer.\n\
2) Request additional documentation. If, in the body of the relevant documentation, is a reference to another section of the document that is directly relevant, respond with the word '{self.rag_prefixes[1]}' followed by the section reference which looks like A.1(A)(i)(aa). \n\
3) State '{self.rag_prefixes[2]}' (and nothing else) in all cases where you are not confident about either of the first two options"
            if len(df_definitions) > 0:
                system_context = system_context + "\nPotentially relevant definition(s):"
                for index, row in df_definitions.iterrows():
                    system_context = system_context + "\n" + row["Definition"]
            if len(df_search_sections) > 0:
                system_context = system_context + "\nPotentially relevant document section(s):"
                for index, row in df_search_sections.iterrows():
                    system_context = system_context + "\n" + row["raw_text"]

            self.logger.info("#################   RAG       #################")
            self.logger.info("\n" + system_context)
            # Create a temporary message list. We will only add the messages to the chat history if we get well formatted answers
            question_messages = [{"role": "system", "content": system_context}] + self.messages # don't change self.messages and don't add system_context to it

            total_tokens = num_tokens_from_string(system_context) + num_tokens_from_string(self.messages[-1]['content']) # just check the system and last user message length
            if total_tokens > 4000 and model_to_use!="gpt-3.5-turbo-16k":
                self.logger.warning("!!! NOTE !!! You have a very long prompt. Switching to the gpt-3.5-turbo-16k model")
                model_to_use = "gpt-3.5-turbo-16k"

            if testing == True:
                self.logger.info("Using canned answers rather than making calls to the openai API")
                initial_response = manual_responses_for_testing[0]
            else:       
                response = openai.ChatCompletion.create(
                                    model=model_to_use,
                                    temperature = temperature,
                                    max_tokens = max_tokens,
                                    messages = question_messages
                                )
                initial_response = response['choices'][0]['message']['content']

            for prefix in self.rag_prefixes:
                if initial_response.startswith(prefix):
                    # Split the string into two parts: the prefix and the remaining text
                    return prefix, initial_response[len(prefix):]

            # now we need to recheck our work!
            self.logger.warning("Initial call did not create a response in the correct format. Retrying")
            self.logger.warning("The response was:")
            self.logger.warning(initial_response)
            despondent_user_context = f"Please check your answer and make sure your answer uses only one of the three permissible forms, {self.rag_prefixes[0]}, {self.rag_prefixes[1]} or {self.rag_prefixes[2]}"
            despondent_user_messages = question_messages + [
                                        {"role": "assistant", "content": initial_response},
                                        {"role": "user", "content": despondent_user_context}]
                                        
            if testing == True and len(manual_responses_for_testing) > 1:
                self.logger.info("Using canned answers rather than making calls to the openai API")
                followup_response_text = manual_responses_for_testing[1]
            else:
                followup_response = openai.ChatCompletion.create(
                                    model=model_to_use,
                                    temperature = temperature,
                                    max_tokens = max_tokens,
                                    messages = despondent_user_messages
                                )
                followup_response_text = followup_response['choices'][0]['message']['content']
            for prefix in self.rag_prefixes:
                if followup_response_text.startswith(prefix):
                    # Split the string into two parts: the prefix and the remaining text
                    return prefix, followup_response_text[len(prefix):]

        return self.rag_prefixes[3], "The LLM was not able to return an acceptable answer. "


    def similarity_search(self, user_context, threshold = 0.15):
        question_embedding = get_ada_embedding(user_context)
        self.logger.info("#################   Similarity Search       #################")
        relevant_definitions = get_closest_nodes(self.df_definitions_all, embedding_column_name = "Embedding", question_embedding = question_embedding, threshold = threshold)
        if len(relevant_definitions) > 0:
            self.logger.info("--   Relevant Definitions")
            for index, row in relevant_definitions.iterrows():
                self.logger.info(f'{row["cosine_distance"]:.4f}: ({row["source"]:>10}): {row["Definition"]}')
        else:
            self.logger.info("--   No relevant definitions found")

        relevant_sections = get_closest_nodes(self.df_text_all, embedding_column_name = "Embedding", question_embedding = question_embedding, threshold = threshold)
        if len(relevant_sections) > 0:
            self.logger.info("--   Relevant Sections")
            for index, row in relevant_sections.iterrows():
                self.logger.info(f'{row["cosine_distance"]:.4f}: {row["section"]:>20}: {row["source"]:>15}: {row["text"]}')

            filtered_relevant_sections = self._filter_relevant_sections(relevant_sections)
            self.logger.info("--   Filtered Sections")
            for index, row in filtered_relevant_sections.iterrows():
                if row["count"] == 1:
                    self.logger.info(f'{row["cosine_distance"]:.4f}            : {row["reference"]:>20}: {row["count"]:>2}')                
                else:
                    self.logger.info(f'{row["cosine_distance"]:.4f} (*min dist): {row["reference"]:>20}: {row["count"]:>2}')                
            filtered_relevant_sections["raw_text"] = filtered_relevant_sections["reference"].apply(self.get_regulation_detail)
            filtered_relevant_sections["token_count"] = filtered_relevant_sections["raw_text"].apply(num_tokens_from_string)

            # max out at 5 pieces of data
            if len(filtered_relevant_sections) > 5:
                self.logger.info("Truncating the number of documents to 5")

            sorted_df = filtered_relevant_sections.sort_values(by="cosine_distance", ascending=True).head(5)

            return relevant_definitions, sorted_df 
        else:
            self.logger.info("--   No relevant sections found")
            return relevant_definitions, relevant_sections 
        

    # Logic to refine the choice of data that will be sent to the LLM
    def _filter_relevant_sections(self, relevant_sections):
        # Get the top result
        search_sections = []
        if len(relevant_sections) > 0:                
            # 1) The top result
            top_result = relevant_sections.iloc[0]["section"]
            cosine_distance = relevant_sections.iloc[0]["cosine_distance"]
            count = len(relevant_sections[relevant_sections['section'] == top_result])
            search_sections.append([top_result, cosine_distance, count])
            self.logger.info(f'Top result: {top_result} with a cosine distance of {cosine_distance:.4f}')

            # 2) The mode
            mode_value_list = relevant_sections['section'].mode()
            mode_value = ""
            if len(mode_value_list) == 1:
                mode_value = mode_value_list[0]
                mode_already_in_search_sections = any(mode_value == sublist[0] for sublist in search_sections) # check if the mode_value appears in the first column of search_sections
                if not mode_already_in_search_sections: # i.e. it is not also the top result
                    sub_frame = relevant_sections[relevant_sections['section'] == mode_value]
                    count = len(sub_frame)
                    minimum_cosine_distance = sub_frame['cosine_distance'].min()
                    search_sections.append([mode_value, minimum_cosine_distance, count])
                    self.logger.info(f"Most common section: {mode_value} with a minimum cosine distance of {minimum_cosine_distance}")
            else:
                self.logger.info("No unique mode")

            # 3) References that are found frequently that are not the mode 
            count_dict = Counter(relevant_sections['section'])
            repeated_items = {k: v for k, v in count_dict.items() if v > 1}
            # Remove the top value and mode from repeated_items if it exists
            if top_result in repeated_items:
                del repeated_items[top_result]
            if mode_value in repeated_items:
                del repeated_items[mode_value]        
            if (len(repeated_items) > 0):
                self.logger.info("References found that occur multiple times")
                for reference, count in repeated_items.items():
                    sub_frame = relevant_sections[relevant_sections['section'] == reference]
                    count = len(sub_frame)
                    minimum_cosine_distance =  sub_frame['cosine_distance'].min()
                    search_sections.append([reference, minimum_cosine_distance, count])
                    self.logger.info(f"Reference: {reference}, Count: {count}, Min Cosine-Distance: {minimum_cosine_distance}")

        
        if len(search_sections) == 1 and len(relevant_sections) > 1: # the case if each section only appears once in the search
            # remove the top search result from the list
            remaining_relevant_sections = relevant_sections[relevant_sections["section"] != search_sections[0][0]]
            self.logger.info(f'Only the top result added but more were found. Adding the next most likely answer')
            if len(remaining_relevant_sections) >= 1:
                second_result = remaining_relevant_sections.iloc[0]
                search_sections.append([second_result['section'], second_result['cosine_distance'], 1])
            if len(remaining_relevant_sections) >= 2:
                third_result = remaining_relevant_sections.iloc[1]
                search_sections.append([third_result['section'], third_result['cosine_distance'], 1])



        # Note the order of the search_section is preserved        
        return pd.DataFrame(search_sections, columns=["reference", "cosine_distance", "count"])

    def get_regulation_detail(self, node_str):
        return get_regulation_detail(node_str, self.df_excon, self.index_checker, non_breaking_space = True)



