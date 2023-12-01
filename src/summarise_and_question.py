# Update the relevant summary row
import openai

system_content_ad = "You are summarizing sections of the 'Currency and Exchange Manual for Authorised Dealers'. When summerizing, do not add filler words like 'the manual says ...' or 'section x says ...', just provide the summary without any explanation. Do not change the spelling of the word authorised, or any of its derivatives, to authorized"
system_content_question_ad = "You are an Authorised Dealer as defined in the 'Currency and Exchange Manual for Authorised Dealers' (Manual) helping to prepare a set of Frequently Asked Questions (FAQs). You will be provided with the Answer, your role to create one or two Questions for the Answer. List your questions as a pipe delimited string. Try to minimize the use of the phrase 'Authorised Dealer'. Alternatives you can use include 'I' or 'bank' or 'dealer'. Below are two examples to guide you. \n\
#### Example 1 Answer\n\
Authorised Dealers can only engage in foreign currency or gold transactions in accordance with the conditions set by the Treasury. The Currency and Exchanges Manual for Authorized Dealers outlines permissions and conditions for such transactions, as well as administrative responsibilities and reporting requirements. It should be read alongside pertinent regulations, without requiring reference to the Financial Surveillance Department.\n\
#### Example 1 Question\n\
Can anyone trade foreign exchange or gold?|Who decides if an FX transaction is allowed?\n\
#### Example 2 Answer\n\
The Financial Surveillance Department reserves the right to amend, grant, or impose further permissions or conditions.\n\
#### Example 2 Question\n\
Will exchange control rules change?"


system_content_adla = "You are describing sections of the 'Currency and Exchange Manual for Authorised Dealers with Limited Authority'. The purpose of the description is to create metadata about the section for the purpose of information retrieval. The purpose is not to summarise or to capture all the detail but rather to describe what is being said in the section.  Do not use phrases like 'The dealer manual says ...' or 'this section describes ...'. Try to avoid creating lists in the summary by using some of the techniques in the examples:\n\
#### Example 1 Input\n\
Z.10 Rules and Regs \n\
    (A) Categories\n\
        (i) Category One\n\
        Lists of requirements for category one \n\
        (ii) Category Two\n\
        Lists of requirements for category two\n\
#### Example 1 Description \n\
The requirements to be categorised as either Category One or Category Two dealer\n\
#### Example 2 Input\n\
Y.6 Compliance \n\
    (F) Risk management\n\
    A risk management programme must include at least the following\n\
        (i) Board approved risk management policy\n\
        the policy to address these topics \n\
            (a) topic 1\n\
            (b) topic 2\n\
        (ii) Positions\n\
            (a) Chief Risk officer\n\
            (b) Chief compliance officer\n\
#### Example 2 Description \n\
Requirements for risk management cover people, positions and internal policy document"

system_content_question_adla = "You are an Authorised Dealer with Limited Authority (ADLA) as defined in the 'Currency and Exchange Manual for ADLAs' (Manual) helping to prepare a set of Frequently Asked Questions (FAQs). You will be provided with the Answer, your role to create between one and three Questions for the Answer. The questions should be high level to cover the different themes in the answer. The questions should not focus on details.\n\
List your questions as a pipe delimited string. Try to minimize the use of the phrase 'Authorised Dealer'. Alternatives you can use include 'I' or 'dealer'. Below are two examples to guide you. \n\
#### Example 1 Answer\n\
Authorised Dealers with Limited Authority can only engage in foreign currency or gold transactions in accordance with the conditions set by the Treasury. The Currency and Exchanges Manual for ADLAs outlines permissions and conditions for such transactions, as well as administrative responsibilities and reporting requirements. It should be read alongside pertinent regulations, without requiring reference to the Financial Surveillance Department.\n\
#### Example 1 Question\n\
Can anyone trade foreign exchange or gold?|Who decides if an FX transaction is allowed?\n\
#### Example 2 Answer\n\
The Financial Surveillance Department reserves the right to amend, grant, or impose further permissions or conditions.\n\
#### Example 2 Question\n\
Will exchange control rules change?"



def get_summary_and_questions_for(text, model):
    system_content = system_content_adla

    user_context = text
    response = openai.ChatCompletion.create(
                        model=model,
                        temperature = 1.0,
                        max_tokens = 500,
                        messages=[
                            {"role": "system", "content": system_content},
                            {"role": "user", "content": user_context},
                        ]
                    )
    summary = response['choices'][0]['message']['content']


    system_content_question = system_content_question_adla
    user_context_question = summary
    response = openai.ChatCompletion.create(
                        model=model,
                        temperature = 1.0,
                        max_tokens = 500,
                        messages=[
                            {"role": "system", "content": system_content_question},
                            {"role": "user", "content": user_context_question},
                        ]
                    )
    questions = response['choices'][0]['message']['content']

    return summary, questions

