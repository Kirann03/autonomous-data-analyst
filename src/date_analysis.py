import pandas as pd


def detect_date_columns(df):

    date_columns = []

    for column in df.columns:

        if pd.api.types.is_datetime64_any_dtype(
            df[column]
        ):
            date_columns.append(column)
            continue

        if df[column].dtype == "object":

            sample = df[column].dropna().head(100)

            if len(sample) == 0:
                continue

            converted = pd.to_datetime(
                sample,
                errors="coerce"
            )

            success_rate = converted.notna().mean()

            if success_rate >= 0.8:

                date_columns.append(column)

    return date_columns


def prepare_date_column(df, column):

    result = df.copy()

    result[column] = pd.to_datetime(
        result[column],
        errors="coerce"
    )

    result = result.dropna(
        subset=[column]
    )

    return result


def get_date_summary(df, column):

    date_df = prepare_date_column(
        df,
        column
    )

    if date_df.empty:

        return None

    return {
        "earliest_date": date_df[column].min(),
        "latest_date": date_df[column].max(),
        "days": (
            date_df[column].max()
            - date_df[column].min()
        ).days,
        "records": len(date_df)
    }


def monthly_summary(
    df,
    date_column,
    value_column
):

    date_df = prepare_date_column(
        df,
        date_column
    )

    if value_column not in date_df.columns:

        return None

    date_df["Month"] = (
        date_df[date_column]
        .dt.to_period("M")
        .astype(str)
    )

    result = (
        date_df
        .groupby("Month")[value_column]
        .sum()
        .reset_index()
    )

    return result