import pandas as pd

df = pd.read_csv("trades_dataset.csv")

print(df.columns.tolist())

if "result_net" in df.columns:
    print(df["result_net"].value_counts(dropna=False))
else:
    print("NO EXISTE result_net")