import openai
import tiktoken

from json import loads
from scipy.spatial import distance
import pandas as pd

def num_tokens_from_string(string: str, encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")) -> int:
    if pd.isna(string):
        return 0
    """Returns the number of tokens in a text string."""
    num_tokens = len(encoding.encode(string))
    return num_tokens

def get_ada_embedding(text, model="text-embedding-ada-002"):
   return openai.Embedding.create(input = [text], model=model)['data'][0]['embedding']

def get_closest_nodes(df, embedding_column_name, question_embedding, threshold = 0.15):
      df['cosine_distance'] = df[embedding_column_name].apply(lambda x: distance.cosine(x, question_embedding))
      closest_nodes = df[df['cosine_distance'] < threshold].sort_values(by='cosine_distance', ascending=True)
      return closest_nodes