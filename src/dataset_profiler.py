import pandas as pd


def profile_dataset(df):

    profile = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_details": []
    }

    for column in df.columns:

        series = df[column]

        details = {
            "column": column,
            "dtype": str(series.dtype),
            "missing_values": int(series.isna().sum()),
            "missing_percentage": round(
                series.isna().mean() * 100,
                2
            ),
            "unique_values": int(
                series.nunique(dropna=True)
            ),
            "sample_values": [
                str(value)
                for value in (
                    series.dropna()
                    .head(5)
                    .tolist()
                )
            ]
        }

        if pd.api.types.is_numeric_dtype(series):

            details["type"] = "numeric"

            details["statistics"] = {
                "mean": round(
                    float(series.mean()),
                    2
                ),
                "median": round(
                    float(series.median()),
                    2
                ),
                "minimum": round(
                    float(series.min()),
                    2
                ),
                "maximum": round(
                    float(series.max()),
                    2
                ),
                "standard_deviation": round(
                    float(series.std()),
                    2
                )
            }

        elif pd.api.types.is_datetime64_any_dtype(series):

            details["type"] = "date"

            valid_dates = series.dropna()

            if not valid_dates.empty:

                details["earliest_date"] = str(
                    valid_dates.min()
                )

                details["latest_date"] = str(
                    valid_dates.max()
                )

        else:

            details["type"] = "categorical"

            top_values = (
                series
                .value_counts()
                .head(10)
                .to_dict()
            )

            details["top_categories"] = {
                str(key): int(value)
                for key, value in top_values.items()
            }

        profile[
            "column_details"
        ].append(details)

    return profile


def create_ai_context(profile):

    context = []

    context.append(
        f"Dataset contains {profile['rows']} rows "
        f"and {profile['columns']} columns."
    )

    context.append(
        "Column information:"
    )

    for column in profile["column_details"]:

        text = (
            f"- {column['column']} | "
            f"Type: {column['type']} | "
            f"Data type: {column['dtype']} | "
            f"Missing: {column['missing_values']} "
            f"({column['missing_percentage']}%) | "
            f"Unique: {column['unique_values']}"
        )

        if "sample_values" in column:

            text += (
                f" | Samples: "
                f"{column['sample_values']}"
            )

        if "statistics" in column:

            stats = column["statistics"]

            text += (
                f" | Mean: {stats['mean']} | "
                f"Median: {stats['median']} | "
                f"Min: {stats['minimum']} | "
                f"Max: {stats['maximum']}"
            )

        if "top_categories" in column:

            text += (
                f" | Top categories: "
                f"{column['top_categories']}"
            )

        if "earliest_date" in column:

            text += (
                f" | Date range: "
                f"{column['earliest_date']} "
                f"to "
                f"{column['latest_date']}"
            )

        context.append(text)

    return "\n".join(context)