import pandas as pd


def get_categorical_columns(df):

    return df.select_dtypes(
        include=[
            "object",
            "string",
            "category"
        ]
    ).columns.tolist()


def category_counts(df, column, limit=15):

    result = (
        df[column]
        .value_counts()
        .head(limit)
        .reset_index()
    )

    result.columns = [
        column,
        "Count"
    ]

    return result


def category_metric_summary(
    df,
    category_column,
    metric_column
):

    if category_column not in df.columns:
        return None

    if metric_column not in df.columns:
        return None

    result = (
        df.groupby(category_column)[metric_column]
        .agg(
            Total="sum",
            Average="mean",
            Minimum="min",
            Maximum="max"
        )
        .reset_index()
    )

    result = result.sort_values(
        "Total",
        ascending=False
    )

    return result


def get_top_category(
    df,
    category_column,
    metric_column
):

    summary = category_metric_summary(
        df,
        category_column,
        metric_column
    )

    if summary is None or summary.empty:
        return None

    return summary.iloc[0]


def get_bottom_category(
    df,
    category_column,
    metric_column
):

    summary = category_metric_summary(
        df,
        category_column,
        metric_column
    )

    if summary is None or summary.empty:
        return None

    return summary.iloc[-1]