import pandas as pd


df = pd.read_csv('./models/target_pred_feature_lstm.csv')
df = df.drop(columns=['month','year','id'])
df.columns