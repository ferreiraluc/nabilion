import pandas as pd

def engolfo_alta(df: pd.DataFrame) -> pd.DataFrame:
    return (
        (df['fechamento'].shift(1) < df['abertura'].shift(1)) &
        (df['fechamento'] > df['abertura'].shift(1)) &
        (df['abertura'] <= df['fechamento'].shift(1))
    )

def engolfo_baixa(df: pd.DataFrame) -> pd.DataFrame:
    return (
        (df['fechamento'].shift(1) > df['abertura'].shift(1)) &
        (df['fechamento'] < df['abertura'].shift(1)) &
        (df['abertura'] >= df['fechamento'].shift(1))
    )

def piercing_line_alta(df: pd.DataFrame) -> pd.DataFrame:
    return None

def piercing_line_baixa(df: pd.DataFrame) -> pd.DataFrame:
    return None