# -*- coding: utf-8 -*-
"""20-03. bert_named_entity_recognition.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1VhLCbyHCo_DHzdU1rfUB2MoR5wI2TBG3
"""

pip install transformers

"""형태소 단위: https://github.com/ukairia777/tensorflow-bert-ner"""

pip install seqeval

import pandas as pd
import urllib.request
import numpy as np
import os
from tqdm import tqdm
from transformers import shape_list, BertTokenizer, BertModel
from seqeval.metrics import f1_score, classification_report

"""# 1. 데이터 로드"""

urllib.request.urlretrieve("https://raw.githubusercontent.com/ukairia777/tensorflow-nlp-tutorial/main/18.%20Fine-tuning%20BERT%20(Cls%2C%20NER%2C%20NLI)/dataset/ner_train_data.csv", filename="ner_train_data.csv")
urllib.request.urlretrieve("https://raw.githubusercontent.com/ukairia777/tensorflow-nlp-tutorial/main/18.%20Fine-tuning%20BERT%20(Cls%2C%20NER%2C%20NLI)/dataset/ner_test_data.csv", filename="ner_test_data.csv")
urllib.request.urlretrieve("https://raw.githubusercontent.com/ukairia777/tensorflow-nlp-tutorial/main/18.%20Fine-tuning%20BERT%20(Cls%2C%20NER%2C%20NLI)/dataset/ner_label.txt", filename="ner_label.txt")

train_ner_df = pd.read_csv("ner_train_data.csv")

train_ner_df.head()

test_ner_df = pd.read_csv("ner_test_data.csv")

test_ner_df.head()

print("학습 데이터 샘플 개수 :", len(train_ner_df))
print("테스트 데이터 샘플 개수 :", len(test_ner_df))

train_data_sentence = [sent.split() for sent in train_ner_df['Sentence'].values]
test_data_sentence = [sent.split() for sent in test_ner_df['Sentence'].values]
train_data_label = [tag.split() for tag in train_ner_df['Tag'].values]
test_data_label = [tag.split() for tag in test_ner_df['Tag'].values]

labels = [label.strip() for label in open('ner_label.txt', 'r', encoding='utf-8')]
print('개체명 태깅 정보 :', labels)

tag_to_index = {tag: index for index, tag in enumerate(labels)}
index_to_tag = {index: tag for index, tag in enumerate(labels)}

print(tag_to_index)
print(index_to_tag)

tag_size = len(tag_to_index)
print('개체명 태깅 정보의 개수 :',tag_size)

"""# 2. 전처리 예시"""

tokenizer = BertTokenizer.from_pretrained("klue/bert-base")

sent = train_data_sentence[1]
label = train_data_label[1]

print('문장 :', sent)
print('레이블 :',label)
print('레이블의 정수 인코딩 :',[tag_to_index[idx] for idx in label])
print('문장의 길이 :', len(sent))
print('레이블의 길이 :', len(label))

tokens = []

for one_word in sent:
  # 각 단어에 대해서 서브워드로 분리.
  # ex) one_word = '쿠마리' ===> subword_tokens = ['쿠', '##마리']
  # ex) one_word = '한동수가' ===> subword_tokens = ['한동', '##수', '##가']
  subword_tokens = tokenizer.tokenize(one_word)
  tokens.extend(subword_tokens)

print('BERT 토크나이저 적용 후 문장 :',tokens)
print('레이블 :', label)
print('레이블의 정수 인코딩 :',[tag_to_index[idx] for idx in label])
print('문장의 길이 :', len(tokens))
print('레이블의 길이 :', len(label))

tokens = []
labels_ids = []

for one_word, label_token in zip(train_data_sentence[1], train_data_label[1]):
  subword_tokens = tokenizer.tokenize(one_word)
  tokens.extend(subword_tokens)
  labels_ids.extend([tag_to_index[label_token]]+ [-100] * (len(subword_tokens) - 1))

print('토큰화 후 문장 :',tokens)
print('레이블 :', ['[PAD]' if idx == -100 else index_to_tag[idx] for idx in labels_ids])
print('레이블의 정수 인코딩 :', labels_ids)
print('문장의 길이 :', len(tokens))
print('레이블의 길이 :', len(labels_ids))

"""# 3. 전처리"""

def convert_examples_to_features(examples, labels, max_seq_len, tokenizer,
                                 pad_token_id_for_segment=0, pad_token_id_for_label=-100):
    cls_token = tokenizer.cls_token
    sep_token = tokenizer.sep_token
    pad_token_id = tokenizer.pad_token_id

    input_ids, attention_masks, token_type_ids, data_labels = [], [], [], []

    for example, label in tqdm(zip(examples, labels), total=len(examples)):
        tokens = []
        labels_ids = []
        for one_word, label_token in zip(example, label):
            # 하나의 단어에 대해서 서브워드로 토큰화
            subword_tokens = tokenizer.tokenize(one_word)
            tokens.extend(subword_tokens)

            # 서브워드 중 첫번째 서브워드만 개체명 레이블을 부여하고 그 외에는 -100으로 채운다.
            labels_ids.extend([tag_to_index[label_token]]+ [pad_token_id_for_label] * (len(subword_tokens) - 1))

        # [CLS]와 [SEP]를 후에 추가할 것을 고려하여 최대 길이를 초과하는 샘플의 경우 max_seq_len - 2의 길이로 변환.
        # ex) max_seq_len = 64라면 길이가 62보다 긴 샘플은 뒷 부분을 자르고 길이 62로 변환.
        special_tokens_count = 2
        if len(tokens) > max_seq_len - special_tokens_count:
            tokens = tokens[:(max_seq_len - special_tokens_count)]
            labels_ids = labels_ids[:(max_seq_len - special_tokens_count)]

        # [SEP]를 추가하는 코드
        # 1. 토큰화 결과의 맨 뒷 부분에 [SEP] 토큰 추가
        # 2. 레이블에도 맨 뒷 부분에 -100 추가.
        tokens += [sep_token]
        labels_ids += [pad_token_id_for_label]

        # [CLS]를 추가하는 코드
        # 1. 토큰화 결과의 앞 부분에 [CLS] 토큰 추가
        # 2. 레이블의 맨 앞 부분에도 -100 추가.
        tokens = [cls_token] + tokens
        labels_ids = [pad_token_id_for_label] + labels_ids

        # 정수 인코딩
        input_id = tokenizer.convert_tokens_to_ids(tokens)

        # 어텐션 마스크 생성
        attention_mask = [1] * len(input_id)

        # 정수 인코딩에 추가할 패딩 길이 연산
        padding_count = max_seq_len - len(input_id)

        # 정수 인코딩, 어텐션 마스크에 패딩 추가
        input_id = input_id + ([pad_token_id] * padding_count)
        attention_mask = attention_mask + ([0] * padding_count)
        # 세그먼트 인코딩.
        token_type_id = [pad_token_id_for_segment] * max_seq_len
        # 레이블 패딩. (단, 이 경우는 패딩 토큰의 ID가 -100)
        label = labels_ids + ([pad_token_id_for_label] * padding_count)

        assert len(input_id) == max_seq_len, "Error with input length {} vs {}".format(len(input_id), max_seq_len)
        assert len(attention_mask) == max_seq_len, "Error with attention mask length {} vs {}".format(len(attention_mask), max_seq_len)
        assert len(token_type_id) == max_seq_len, "Error with token type length {} vs {}".format(len(token_type_id), max_seq_len)
        assert len(label) == max_seq_len, "Error with labels length {} vs {}".format(len(label), max_seq_len)

        input_ids.append(input_id)
        attention_masks.append(attention_mask)
        token_type_ids.append(token_type_id)
        data_labels.append(label)

    input_ids = np.array(input_ids, dtype=int)
    attention_masks = np.array(attention_masks, dtype=int)
    token_type_ids = np.array(token_type_ids, dtype=int)
    data_labels = np.asarray(data_labels, dtype=np.int32)

    return (input_ids, attention_masks, token_type_ids), data_labels

X_train, y_train = convert_examples_to_features(train_data_sentence, train_data_label, max_seq_len=128, tokenizer=tokenizer)

len(X_train)

len(y_train)

print('기존 원문 :', train_data_sentence[0])
print('기존 레이블 :', train_data_label[0])
print('-' * 50)
print('토큰화 후 원문 :', [tokenizer.decode([word]) for word in X_train[0][0]])
print('토큰화 후 레이블 :', ['[PAD]' if idx == -100 else index_to_tag[idx] for idx in y_train[0]])
print('-' * 50)
print('정수 인코딩 결과 :', X_train[0][0])
print('정수 인코딩 레이블 :', y_train[0])

print('세그먼트 인코딩 :', X_train[2][0])
print('어텐션 마스크 :', X_train[1][0])

X_test, y_test = convert_examples_to_features(test_data_sentence, test_data_label, max_seq_len=128, tokenizer=tokenizer)

"""## 4. nn.CrossEntropy의 -100 무시"""

import torch
import torch.nn as nn

# 모델의 예측값
outputs_with_ignore = torch.tensor([[1.0, 2.0, 3.0], # 값이 가장 큰 위치의 인덱스가 정답
                                    [2.0, 1.0, 3.0],
                                    [3.0, 2.0, 1.0],
                                    [1.0, 3.0, 2.0]])
                                    # [2, 2, 0, 1]

# 레이블 (-100인 레이블에 대해서는 오차를 계산하지 않습니다.)
targets_with_ignore = torch.tensor([2, -100, 0, -100])

# -100을 무시하는 설정으로 손실 계산
loss_fn_with_ignore = nn.CrossEntropyLoss(ignore_index=-100)
loss_with_ignore = loss_fn_with_ignore(outputs_with_ignore, targets_with_ignore)

# 오차
print(f'Loss with ignore_index=-100: {loss_with_ignore.item()}')

# 위의 데이터에서 -100이 있는 위치의 값을 실제로 제거한 데이터
# 모델의 예측값
outputs = torch.tensor([[1.0, 2.0, 3.0],
                        [3.0, 2.0, 1.0]])
# 레이블
targets = torch.tensor([2, 0])

loss_fn = nn.CrossEntropyLoss()
loss = loss_fn(outputs, targets)

# 오차
print(f'calculated loss: {loss.item()}')

"""# 5. 모델링과 학습"""

import torch
from transformers import BertForTokenClassification
from torch.optim import Adam
from torch.utils.data import TensorDataset, DataLoader
from seqeval.metrics import f1_score, classification_report

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = BertForTokenClassification.from_pretrained("klue/bert-base", num_labels=tag_size)
optimizer = Adam(model.parameters(), lr=5e-5)
model.to(device)

def sequences_to_tags(label_ids, pred_ids, index_to_tag):
    # label_ids: 실제 레이블의 인덱스 시퀀스 리스트 (2D 리스트)
    # pred_ids: 예측된 레이블의 인덱스 시퀀스 리스트 (2D 리스트)
    # index_to_tag: 인덱스를 태그로 변환하는 딕셔너리

    label_list = []
    pred_list = []

    # 각 시퀀스에 대해 반복
    for i in range(0, len(label_ids)):
        label_tag = []  # 현재 시퀀스의 실제 레이블 태그들을 저장할 리스트
        pred_tag = []   # 현재 시퀀스의 예측된 레이블 태그들을 저장할 리스트

        # 각 시퀀스의 레이블 및 예측값 쌍에 대해 반복
        for label_index, pred_index in zip(label_ids[i], pred_ids[i]):
            if label_index != -100:  # 유효하지 않은 레이블 (예: 패딩 등) 제외
                label_tag.append(index_to_tag[label_index])  # 실제 레이블 태그 추가
                pred_tag.append(index_to_tag[pred_index])    # 예측된 레이블 태그 추가

        label_list.append(label_tag)  # 현재 시퀀스의 실제 레이블 태그 리스트를 전체 리스트에 추가
        pred_list.append(pred_tag)    # 현재 시퀀스의 예측된 레이블 태그 리스트를 전체 리스트에 추가

    return label_list, pred_list  # 실제 레이블과 예측된 레이블의 태그 리스트 반환

def evaluate(model, test_loader, index_to_tag):
    # 모델을 평가 모드로 전환 (드롭아웃 등 비활성화)
    model.eval()
    total_labels, total_preds = [], []  # 전체 레이블과 예측값을 저장할 리스트 초기화

    # 그레디언트 계산을 비활성화하여 메모리 사용량 및 연산 속도를 최적화
    with torch.no_grad():
        # 테스트 데이터셋의 각 배치에 대해 반복
        for input_ids, attention_masks, token_type_ids, labels in test_loader:
            # 데이터를 GPU 또는 지정된 디바이스로 이동
            input_ids = input_ids.to(device)
            attention_masks = attention_masks.to(device)
            token_type_ids = token_type_ids.to(device)
            labels = labels.to(device)

            # 모델에 입력 데이터를 주고 예측값(logits) 출력
            outputs = model(input_ids, attention_mask=attention_masks, token_type_ids=token_type_ids)

            # 예측값(logits)을 CPU로 이동시키고 넘파이 배열로 변환
            logits = outputs.logits.detach().cpu().numpy()

            # 레이블을 CPU로 이동시키고 넘파이 배열로 변환
            labels = labels.cpu().numpy()

            # 예측값에서 가장 높은 확률의 인덱스를 선택하여 예측된 레이블 생성
            y_predicted = np.argmax(logits, axis=2)

            # 실제 레이블과 예측된 레이블을 태그로 변환
            label_list, pred_list = sequences_to_tags(labels, y_predicted, index_to_tag)

            # 전체 레이블 리스트와 예측 리스트에 현재 배치의 결과를 추가
            total_labels.extend(label_list)
            total_preds.extend(pred_list)

    # 전체 레이블과 예측값에 대한 F1 점수를 계산
    score = f1_score(total_labels, total_preds, suffix=True)

    # F1 점수를 출력
    print(' - f1: {:04.2f}'.format(score * 100))

    # 전체 레이블과 예측값에 대한 분류 리포트를 출력
    print(classification_report(total_labels, total_preds, suffix=True))

batch_size = 32

# 이 부분은 convert_examples_to_features에서 반환하는 형식에 맞게 텐서를 분할합니다.
# X_train과 y_train은 학습 데이터, X_test와 y_test는 테스트 데이터로 사용됩니다.

# 학습 데이터에서 각 입력 값(input_ids, attention_masks, token_type_ids)과 레이블(labels)을 추출
train_input_ids, train_attention_masks, train_token_type_ids = X_train
train_labels = y_train

# 테스트 데이터에서 각 입력 값(input_ids, attention_masks, token_type_ids)과 레이블(labels)을 추출
test_input_ids, test_attention_masks, test_token_type_ids = X_test
test_labels = y_test

# 학습 데이터의 각 부분을 파이토치 텐서로 변환 (정수형)
train_input_ids = torch.tensor(train_input_ids, dtype=torch.long)
train_attention_masks = torch.tensor(train_attention_masks, dtype=torch.long)
train_token_type_ids = torch.tensor(train_token_type_ids, dtype=torch.long)
train_labels = torch.tensor(train_labels, dtype=torch.long)

# 테스트 데이터의 각 부분을 파이토치 텐서로 변환 (정수형)
test_input_ids = torch.tensor(test_input_ids, dtype=torch.long)
test_attention_masks = torch.tensor(test_attention_masks, dtype=torch.long)
test_token_type_ids = torch.tensor(test_token_type_ids, dtype=torch.long)
test_labels = torch.tensor(test_labels, dtype=torch.long)

# 학습 데이터와 테스트 데이터 텐서들을 하나의 TensorDataset으로 묶음
train_data = TensorDataset(train_input_ids, train_attention_masks, train_token_type_ids, train_labels)
test_data = TensorDataset(test_input_ids, test_attention_masks, test_token_type_ids, test_labels)

# 학습 데이터와 테스트 데이터에 대해서 데이터 로더를 생성, batch_size로 데이터를 묶어 모델에 전달할 준비를 함
train_loader = DataLoader(train_data, batch_size=batch_size)
test_loader = DataLoader(test_data, batch_size=batch_size)

import tqdm

steps = len(train_input_ids) // batch_size + 1
print(steps)

EPOCHS = 3  # 학습을 반복할 횟수(에포크 수)를 설정

# 설정한 에포크 수만큼 반복
for epoch in range(EPOCHS):
    model.train()  # 모델을 학습 모드로 전환 (드롭아웃 등 활성화)

    # 학습 데이터 로더에서 배치를 하나씩 가져와서 반복
    for input_ids, attention_masks, token_type_ids, labels in tqdm.tqdm(train_loader, total=steps):
        # 각 입력 데이터를 GPU 또는 지정된 디바이스로 이동
        input_ids = input_ids.to(device)
        attention_masks = attention_masks.to(device)
        token_type_ids = token_type_ids.to(device)
        labels = labels.to(device)

        # 옵티마이저의 그레디언트를 초기화
        optimizer.zero_grad()

        # 모델에 데이터를 입력하여 예측값(outputs)을 계산하고 손실(loss)도 계산
        outputs = model(input_ids, attention_mask=attention_masks, token_type_ids=token_type_ids, labels=labels)
        loss = outputs.loss  # 손실 값 추출

        # 역전파를 통해 그레디언트를 계산
        loss.backward()

        # 옵티마이저를 통해 모델 파라미터를 업데이트
        optimizer.step()

    # 한 에포크가 끝난 후, 모델을 평가하여 성능을 측정
    evaluate(model, test_loader, index_to_tag)

"""# 6. 예측"""

def convert_examples_to_features_for_prediction(examples, max_seq_len, tokenizer,
                                 pad_token_id_for_segment=0, pad_token_id_for_label=-100):
    cls_token = tokenizer.cls_token
    sep_token = tokenizer.sep_token
    pad_token_id = tokenizer.pad_token_id

    input_ids, attention_masks, token_type_ids, label_masks = [], [], [], []

    for example in tqdm.tqdm(examples):
        tokens = []
        label_mask = []
        for one_word in example:
            # 하나의 단어에 대해서 서브워드로 토큰화
            subword_tokens = tokenizer.tokenize(one_word)
            tokens.extend(subword_tokens)\
            # 서브워드 중 첫번째 서브워드를 제외하고 그 뒤의 서브워드들은 -100으로 채운다.
            label_mask.extend([0]+ [pad_token_id_for_label] * (len(subword_tokens) - 1))

        # [CLS]와 [SEP]를 후에 추가할 것을 고려하여 최대 길이를 초과하는 샘플의 경우 max_seq_len - 2의 길이로 변환.
        # ex) max_seq_len = 64라면 길이가 62보다 긴 샘플은 뒷 부분을 자르고 길이 62로 변환.
        special_tokens_count = 2
        if len(tokens) > max_seq_len - special_tokens_count:
            tokens = tokens[:(max_seq_len - special_tokens_count)]
            label_mask = label_mask[:(max_seq_len - special_tokens_count)]

        # [SEP]를 추가하는 코드
        # 1. 토큰화 결과의 맨 뒷 부분에 [SEP] 토큰 추가
        # 2. 레이블에도 맨 뒷 부분에 -100 추가.
        tokens += [sep_token]
        label_mask += [pad_token_id_for_label]

        # [CLS]를 추가하는 코드
        # 1. 토큰화 결과의 앞 부분에 [CLS] 토큰 추가
        # 2. 레이블의 맨 앞 부분에도 -100 추가.
        tokens = [cls_token] + tokens
        label_mask = [pad_token_id_for_label] + label_mask
        input_id = tokenizer.convert_tokens_to_ids(tokens)
        attention_mask = [1] * len(input_id)

        # 정수 인코딩에 추가할 패딩 길이 연산
        padding_count = max_seq_len - len(input_id)

         # 정수 인코딩, 어텐션 마스크에 패딩 추가
        input_id = input_id + ([pad_token_id] * padding_count)
        attention_mask = attention_mask + ([0] * padding_count)

        # 세그먼트 인코딩.
        token_type_id = [pad_token_id_for_segment] * max_seq_len

        # 레이블 패딩. (단, 이 경우는 패딩 토큰의 ID가 -100)
        label_mask = label_mask + ([pad_token_id_for_label] * padding_count)

        assert len(input_id) == max_seq_len, "Error with input length {} vs {}".format(len(input_id), max_seq_len)
        assert len(attention_mask) == max_seq_len, "Error with attention mask length {} vs {}".format(len(attention_mask), max_seq_len)
        assert len(token_type_id) == max_seq_len, "Error with token type length {} vs {}".format(len(token_type_id), max_seq_len)
        assert len(label_mask) == max_seq_len, "Error with labels length {} vs {}".format(len(label_mask), max_seq_len)

        input_ids.append(input_id)
        attention_masks.append(attention_mask)
        token_type_ids.append(token_type_id)
        label_masks.append(label_mask)

    input_ids = np.array(input_ids, dtype=int)
    attention_masks = np.array(attention_masks, dtype=int)
    token_type_ids = np.array(token_type_ids, dtype=int)
    label_masks = np.asarray(label_masks, dtype=np.int32)

    return (input_ids, attention_masks, token_type_ids), label_masks

test_data_sentence[:5]

X_pred, label_masks = convert_examples_to_features_for_prediction(test_data_sentence[:5], max_seq_len=128, tokenizer=tokenizer)

print('기존 원문 :', test_data_sentence[0])
print('-' * 50)
print('토큰화 후 원문 :', [tokenizer.decode([word]) for word in X_pred[0][0]])
print('레이블 마스크 :', ['[PAD]' if idx == -100 else '[FIRST]' for idx in label_masks[0]])

def ner_prediction(examples, max_seq_len, tokenizer, model, device):
    examples = [sent.split() for sent in examples]
    X_pred, label_masks = convert_examples_to_features_for_prediction(examples, max_seq_len=128, tokenizer=tokenizer)

    # Convert input_ids, attention_masks, and token_type_ids to tensors
    input_ids, attention_masks, token_type_ids = X_pred
    input_ids = torch.tensor(input_ids, dtype=torch.long).to(device)
    attention_masks = torch.tensor(attention_masks, dtype=torch.long).to(device)
    token_type_ids = torch.tensor(token_type_ids, dtype=torch.long).to(device)

    label_masks = torch.tensor(label_masks, dtype=torch.long).to(device)

    model.eval()
    with torch.no_grad():
        outputs = model(input_ids, attention_mask=attention_masks, token_type_ids=token_type_ids)
        logits = outputs.logits.detach().cpu().numpy()
        y_predicted = np.argmax(logits, axis=2)

    pred_list = []
    result_list = []

    # ex) 모델의 예측값 디코딩 과정
    # 예측값(y_predicted)에서 레이블 마스크(label_masks)의 값이 -100인 동일 위치의 값을 삭제
    # label_masks : [-100 0 -100 0 -100]
    # y_predicted : [  0  1   0  2   0 ] ==> [1 2] ==> 최종 예측(pred_tag) : [PER-B PER-I]
    for i in range(0, len(label_masks)):
        pred_tag = []
        for label_index, pred_index in zip(label_masks[i], y_predicted[i]):
            if label_index != -100:
                pred_tag.append(index_to_tag[pred_index])

        pred_list.append(pred_tag)

    for example, pred in zip(examples, pred_list):
        one_sample_result = []
        for one_word, label_token in zip(example, pred):
            one_sample_result.append((one_word, label_token))
        result_list.append(one_sample_result)

    return result_list

sent1 = '오리온스는 리그 최정상급 포인트가드 김동훈을 앞세우는 빠른 공수전환이 돋보이는 팀이다'
sent2 = '하이신사에 속한 섬들도 위로 솟아 있는데 타인은 살고 있어요'

test_samples = [sent1, sent2]

result_list = ner_prediction(test_samples, max_seq_len=128, tokenizer=tokenizer, model=model, device=device)

result_list

# my_bert_model이라는 폴더가 생기고 그 안에 모델 파일들이 저장됨.
model_save_path = "./my_bert_model"
model.save_pretrained(model_save_path)

model = BertForTokenClassification.from_pretrained(model_save_path)