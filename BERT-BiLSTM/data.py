from functools import partial

import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder
import re
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

# Make MyDataset
class MyDataset(Dataset):
    def __init__(self, sentences, labels, method_name, model_name):
        self.sentences = sentences
        self.labels = labels
        self.method_name = method_name
        self.model_name = model_name
        dataset = list()
        index = 0
        for data in sentences:
            tokens = data.split(' ')
            labels_id = labels[index]
            index += 1
            dataset.append((tokens, labels_id))
        self._dataset = dataset

    def __getitem__(self, index):
        return self._dataset[index]

    def __len__(self):
        return len(self.sentences)


# Make tokens for every batch
def my_collate(batch, tokenizer):
    tokens, label_ids = map(list, zip(*batch))

    text_ids = tokenizer(tokens,
                         padding=True,
                         truncation=True,
                         max_length=320,
                         is_split_into_words=True,
                         add_special_tokens=True,
                         return_tensors='pt')
    # print(1,text_ids['position_ids'])
    # print(2,text_ids['attention_mask'])
    # print(3,text_ids['input_ids'])
    return text_ids, torch.tensor(label_ids)


# Load dataset
def load_dataset(tokenizer, train_batch_size, test_batch_size, model_name, method_name, workers):
    # data = pd.read_csv('datasets.csv', sep=None, header=0, encoding='utf-8', engine='python')
    # len1 = int(len(list(data['labels'])) * 0.1)
    # labels = list(data['labels'])[0:len1]
    # sentences = list(data['sentences'])[0:len1]
    
    # Load the reduced dataset
    df = pd.read_csv('/media/yatipa_drive/sep_ana/reduced_dataset.csv')

    # Preprocess the data
    df['review_text'].fillna('', inplace=True)

    # Function to clean text
    def clean_text(text):
        text = re.sub(r'[^A-Za-z\s]', '', text)  # Remove non-English characters
        text = text.lower()  # Convert to lowercase
        text = re.sub(r'\s+', ' ', text).strip()  # Remove extra spaces
        return text

    # Apply text cleaning
    df['cleaned_review_text'] = df['review_text'].apply(clean_text)

    # Function to detect language and filter out non-English reviews
    def is_english(text):
        try:
            return detect(text) == 'en'
        except LangDetectException:
            return False

    # Filter out non-English reviews
    df = df[df['cleaned_review_text'].apply(is_english)]

    # Encode the labels
    label_encoder = LabelEncoder()
    df['sentiment'] = label_encoder.fit_transform(df['sentiment'])
    df = df[df.sentiment != 3] ##### --- 
    labels = list(df['sentiment'])
    sentences = list(df['cleaned_review_text'])

    # split train_set and test_set
    tr_sen, te_sen, tr_lab, te_lab = train_test_split(sentences, labels, train_size=0.8)
    # Dataset
    train_set = MyDataset(tr_sen, tr_lab, method_name, model_name)
    test_set = MyDataset(te_sen, te_lab, method_name, model_name)
    # DataLoader
    collate_fn = partial(my_collate, tokenizer=tokenizer)
    train_loader = DataLoader(train_set, batch_size=train_batch_size, shuffle=True, num_workers=workers,
                              collate_fn=collate_fn, pin_memory=True)
    test_loader = DataLoader(test_set, batch_size=test_batch_size, shuffle=True, num_workers=workers,
                             collate_fn=collate_fn, pin_memory=True)
    return train_loader, test_loader
