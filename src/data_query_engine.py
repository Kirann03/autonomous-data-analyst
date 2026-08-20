import pandas as pd
import re


def find_column(df, text):

    text = text.lower()

    for column in df.columns:

        if str(column).lower() in text:

            return column

    return None


def query_dataset(df, question):

    if df is None or df.empty:
        return "The dataset is empty."


    q = question.lower().strip()


    numeric_columns = (
        df.select_dtypes(
            include="number"
        ).columns.tolist()
    )


    categorical_columns = (
        df.select_dtypes(
            include=[
                "object",
                "string",
                "category"
            ]
        ).columns.tolist()
    )


    # ==========================================
    # ROW COUNT
    # ==========================================

    if (
        "how many rows" in q
        or "number of rows" in q
        or "how many records" in q
        or "number of records" in q
    ):

        return (
            f"The dataset contains "
            f"{len(df):,} rows."
        )


    # ==========================================
    # COLUMN COUNT
    # ==========================================

    if (
        "how many columns" in q
        or "number of columns" in q
    ):

        return (
            f"The dataset contains "
            f"{len(df.columns)} columns."
        )


    # ==========================================
    # COLUMN LIST
    # ==========================================

    if (
        "what columns" in q
        or "list columns" in q
        or "column names" in q
    ):

        return (
            "Available columns:\n\n"
            + "\n".join(
                f"- {column}"
                for column in df.columns
            )
        )


    # ==========================================
    # MISSING VALUES
    # ==========================================

    if (
        "missing values" in q
        or "missing data" in q
        or "null values" in q
        or "nulls" in q
    ):

        missing = (
            df.isnull()
            .sum()
        )

        missing = (
            missing[missing > 0]
            .sort_values(
                ascending=False
            )
        )

        if missing.empty:

            return (
                "There are no missing values "
                "in the dataset."
            )

        result = []

        for column, count in missing.items():

            percentage = (
                count / len(df) * 100
            )

            result.append(
                f"- {column}: "
                f"{count:,} "
                f"({percentage:.2f}%)"
            )

        return (
            "Missing values:\n\n"
            + "\n".join(result)
        )


    # ==========================================
    # DUPLICATES
    # ==========================================

    if "duplicate" in q:

        count = (
            df.duplicated()
            .sum()
        )

        return (
            f"The dataset contains "
            f"{count:,} duplicate rows."
        )


    # ==========================================
    # TOP N BY NUMERIC COLUMN
    # ==========================================

    top_match = re.search(
        r"(?:top|highest|best)\s*(\d+)?",
        q
    )


    if top_match:

        n = (
            int(top_match.group(1))
            if top_match.group(1)
            else 5
        )


        target_column = None


        for column in numeric_columns:

            if (
                str(column).lower()
                in q
            ):

                target_column = column
                break


        if target_column:

            result = (
                df[
                    [
                        target_column
                    ]
                ]
                .sort_values(
                    target_column,
                    ascending=False
                )
                .head(n)
            )


            return (
                f"Top {n} records by "
                f"'{target_column}':\n\n"
                + result.to_string(
                    index=False
                )
            )


    # ==========================================
    # BOTTOM N BY NUMERIC COLUMN
    # ==========================================

    bottom_match = re.search(
        r"(?:bottom|lowest|worst)\s*(\d+)?",
        q
    )


    if bottom_match:

        n = (
            int(bottom_match.group(1))
            if bottom_match.group(1)
            else 5
        )


        target_column = None


        for column in numeric_columns:

            if (
                str(column).lower()
                in q
            ):

                target_column = column
                break


        if target_column:

            result = (
                df[
                    [
                        target_column
                    ]
                ]
                .sort_values(
                    target_column,
                    ascending=True
                )
                .head(n)
            )


            return (
                f"Bottom {n} records by "
                f"'{target_column}':\n\n"
                + result.to_string(
                    index=False
                )
            )


    # ==========================================
    # TOTAL / SUM
    # ==========================================

    for column in numeric_columns:

        if (
            str(column).lower()
            in q
            and (
                "total" in q
                or "sum" in q
            )
        ):

            total = (
                df[column]
                .sum()
            )

            return (
                f"The total of "
                f"'{column}' is "
                f"{total:,.2f}."
            )


    # ==========================================
    # AVERAGE / MEAN
    # ==========================================

    for column in numeric_columns:

        if (
            str(column).lower()
            in q
            and (
                "average" in q
                or "mean" in q
            )
        ):

            value = (
                df[column]
                .mean()
            )

            return (
                f"The average of "
                f"'{column}' is "
                f"{value:,.2f}."
            )


    # ==========================================
    # MEDIAN
    # ==========================================

    for column in numeric_columns:

        if (
            str(column).lower()
            in q
            and "median" in q
        ):

            value = (
                df[column]
                .median()
            )

            return (
                f"The median of "
                f"'{column}' is "
                f"{value:,.2f}."
            )


    # ==========================================
    # MAXIMUM
    # ==========================================

    for column in numeric_columns:

        if (
            str(column).lower()
            in q
            and (
                "maximum" in q
                or "highest value" in q
                or "max" in q
            )
        ):

            value = (
                df[column]
                .max()
            )

            return (
                f"The maximum value of "
                f"'{column}' is "
                f"{value:,.2f}."
            )


    # ==========================================
    # MINIMUM
    # ==========================================

    for column in numeric_columns:

        if (
            str(column).lower()
            in q
            and (
                "minimum" in q
                or "lowest value" in q
                or "min" in q
            )
        ):

            value = (
                df[column]
                .min()
            )

            return (
                f"The minimum value of "
                f"'{column}' is "
                f"{value:,.2f}."
            )


    # ==========================================
    # UNIQUE VALUES
    # ==========================================

    if (
        "unique values" in q
        or "unique categories" in q
    ):

        result = []

        for column in df.columns:

            count = (
                df[column]
                .nunique()
            )

            result.append(
                f"- {column}: "
                f"{count:,}"
            )

        return (
            "Unique values by column:\n\n"
            + "\n".join(result)
        )


    # ==========================================
    # CATEGORY COUNTS
    # ==========================================

    for column in categorical_columns:

        if (
            str(column).lower()
            in q
            and (
                "categories" in q
                or "category" in q
                or "count" in q
                or "distribution" in q
            )
        ):

            counts = (
                df[column]
                .value_counts()
                .head(20)
            )

            return (
                f"Category distribution "
                f"for '{column}':\n\n"
                + counts.to_string()
            )


    # ==========================================
    # GROUP BY CATEGORY + NUMERIC METRIC
    # ==========================================

    selected_category = None
    selected_metric = None


    for column in categorical_columns:

        if (
            str(column).lower()
            in q
        ):

            selected_category = column
            break


    for column in numeric_columns:

        if (
            str(column).lower()
            in q
        ):

            selected_metric = column
            break


    if (
        selected_category
        and selected_metric
        and (
            "by" in q
            or "compare" in q
            or "per" in q
            or "each" in q
        )
    ):

        if (
            "average" in q
            or "mean" in q
        ):

            grouped = (
                df.groupby(
                    selected_category
                )[selected_metric]
                .mean()
                .sort_values(
                    ascending=False
                )
            )

            return (
                f"Average '{selected_metric}' "
                f"by '{selected_category}':\n\n"
                + grouped.to_string()
            )


        grouped = (
            df.groupby(
                selected_category
            )[selected_metric]
            .sum()
            .sort_values(
                ascending=False
            )
        )


        return (
            f"Total '{selected_metric}' "
            f"by '{selected_category}':\n\n"
            + grouped.to_string()
        )


    # ==========================================
    # DATASET OVERVIEW
    # ==========================================

    if (
        "overview" in q
        or "dataset summary" in q
        or "summarize dataset" in q
    ):

        return (
            f"Dataset overview:\n\n"
            f"- Rows: {len(df):,}\n"
            f"- Columns: {len(df.columns)}\n"
            f"- Numeric columns: "
            f"{len(numeric_columns)}\n"
            f"- Categorical columns: "
            f"{len(categorical_columns)}\n"
            f"- Missing values: "
            f"{df.isnull().sum().sum():,}\n"
            f"- Duplicate rows: "
            f"{df.duplicated().sum():,}"
        )


    return None