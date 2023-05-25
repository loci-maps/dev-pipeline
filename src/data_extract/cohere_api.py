import cohere
import pandas as pd

from time import time, sleep
from tqdm import tqdm

from src.utils import chunk_text


def create_embeddings(df, api_key, rate_limit_calls=100, rate_limit_duration=60, batch_size=96):
    co = cohere.Client(api_key)
    embeddings = []

    start_time = time()
    call_count = 0

    for ix, row in df.iterrows():
        text_chunks = chunk_text(row['text'])

        for chunk in text_chunks:
            embeddings.append({
                'filename': row['filename'],
                'index': ix,
                'chunk_text': chunk,
                'embedding': None
            })

    embedding_batches = [embeddings[ix:ix + batch_size] for ix in range(0, len(embeddings), batch_size)]

    for batch in tqdm(embedding_batches, total=len(embedding_batches), desc="Embedding text"):
        texts = [item['chunk_text'] for item in batch]
        response = co.embed(texts=texts, model='large', truncate='END')

        for ix, embedding in enumerate(response.embeddings):
            batch[ix]['embedding'] = embedding

        call_count += 1

        if call_count >= rate_limit_calls:
            elapsed_time = time() - start_time

            if elapsed_time < rate_limit_duration:
                sleep(rate_limit_duration - elapsed_time)

            start_time = time()
            call_count = 0

    df_embeddings = pd.DataFrame(embeddings)
    remaining_keys = list(df.keys())
    remaining_keys.remove('text')
    df_embeddings = df_embeddings.merge(df[remaining_keys], on='filename', how='left')
    embeddings = df_embeddings['embedding'].apply(pd.Series).to_numpy()
    filenames = df_embeddings['filename'].to_numpy()
    return embeddings, filenames
