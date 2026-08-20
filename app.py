import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from src.ai_engine import generate_analysis
from src.insights_engine import generate_business_insights
from src.data_query_engine import query_dataset
from src.date_analysis import detect_date_columns
from src.date_analysis import get_date_summary
from src.date_analysis import monthly_summary
from src.categorical_analysis import get_categorical_columns
from src.categorical_analysis import category_counts
from src.categorical_analysis import category_metric_summary
from src.categorical_analysis import get_top_category
from src.categorical_analysis import get_bottom_category
from src.dataset_profiler import profile_dataset
from src.dataset_profiler import create_ai_context
from src.agent_engine import PlanValidationError, run_autonomous_analysis


st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="🤖",
    layout="wide"
)


st.title("🤖 AI Data Analyst")

st.write(
    "Upload your dataset and let the application "
    "perform end-to-end data analysis."
)

st.divider()


st.header("📁 Upload Your Dataset")

uploaded_file = st.file_uploader(
    "Upload a CSV or Excel file",
    type=["csv", "xlsx"]
)


if uploaded_file is not None:

    try:

        if uploaded_file.name.lower().endswith(".csv"):

            df = pd.read_csv(
                uploaded_file,
                encoding="latin1"
            )

        else:

            df = pd.read_excel(
                uploaded_file
            )


        st.success(
            f"Successfully loaded: {uploaded_file.name}"
        )


        st.divider()


        st.header("📊 Dataset Overview")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Rows",
                f"{df.shape[0]:,}"
            )

        with col2:
            st.metric(
                "Columns",
                df.shape[1]
            )

        with col3:
            st.metric(
                "Missing Values",
                f"{df.isnull().sum().sum():,}"
            )

        with col4:
            st.metric(
                "Duplicate Rows",
                f"{df.duplicated().sum():,}"
            )


        st.divider()


        st.header("🛡️ Data Quality Analysis")

        missing_total = df.isnull().sum().sum()

        duplicate_total = df.duplicated().sum()

        numeric_columns = (
            df.select_dtypes(
                include="number"
            ).columns.tolist()
        )

        categorical_columns = (
            df.select_dtypes(
                include=[
                    "object",
                    "category",
                    "string"
                ]
            ).columns.tolist()
        )


        q1, q2, q3 = st.columns(3)

        with q1:
            st.metric(
                "Missing Values",
                f"{missing_total:,}"
            )

        with q2:
            st.metric(
                "Duplicate Rows",
                f"{duplicate_total:,}"
            )

        with q3:
            st.metric(
                "Numeric Columns",
                len(numeric_columns)
            )


        st.divider()


        st.header("🧹 Automatic Data Cleaning")

        clean_button = st.button(
            "🧹 Clean Dataset",
            type="primary",
            use_container_width=True
        )


        if clean_button:

            cleaned_df = df.copy()

            original_rows = len(
                cleaned_df
            )

            original_columns = len(
                cleaned_df.columns
            )


            cleaned_df.columns = (
                cleaned_df.columns
                .astype(str)
                .str.strip()
            )


            empty_columns = [
                column
                for column in cleaned_df.columns
                if cleaned_df[column].isna().all()
            ]


            if empty_columns:

                cleaned_df = cleaned_df.drop(
                    columns=empty_columns
                )


            text_columns = (
                cleaned_df.select_dtypes(
                    include=[
                        "object",
                        "string"
                    ]
                ).columns
            )


            for column in text_columns:

                cleaned_df[column] = (
                    cleaned_df[column]
                    .astype("string")
                    .str.strip()
                )

                cleaned_df[column] = (
                    cleaned_df[column]
                    .replace(
                        {
                            "": pd.NA,
                            "nan": pd.NA,
                            "None": pd.NA
                        }
                    )
                )


            cleaned_df = (
                cleaned_df.drop_duplicates()
            )


            cleaned_df = (
                cleaned_df.replace(
                    [np.inf, -np.inf],
                    np.nan
                )
            )


            st.session_state[
                "cleaned_df"
            ] = cleaned_df


            st.success(
                "✅ Dataset cleaned successfully!"
            )


            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "Original Rows",
                    f"{original_rows:,}"
                )

            with c2:
                st.metric(
                    "Cleaned Rows",
                    f"{len(cleaned_df):,}"
                )

            with c3:
                st.metric(
                    "Rows Removed",
                    f"{original_rows - len(cleaned_df):,}"
                )

            with c4:
                st.metric(
                    "Columns Removed",
                    f"{original_columns - len(cleaned_df.columns):,}"
                )


            st.divider()


            st.subheader(
                "📥 Download Cleaned Dataset"
            )


            cleaned_csv = (
                cleaned_df
                .to_csv(index=False)
                .encode("utf-8")
            )


            st.download_button(
                label="📥 Download Cleaned CSV",
                data=cleaned_csv,
                file_name="cleaned_dataset.csv",
                mime="text/csv",
                use_container_width=True
            )


        if "cleaned_df" in st.session_state:

            cleaned_df = (
                st.session_state[
                    "cleaned_df"
                ]
            )


            numeric_columns = (
                cleaned_df.select_dtypes(
                    include="number"
                ).columns.tolist()
            )


            categorical_columns = (
                cleaned_df.select_dtypes(
                    include=[
                        "object",
                        "string",
                        "category"
                    ]
                ).columns.tolist()
            )


            st.divider()


            st.header(
                "📈 Exploratory Data Analysis"
            )


            if numeric_columns:

                st.subheader(
                    "📊 Numerical Statistics"
                )


                statistics = (
                    cleaned_df[
                        numeric_columns
                    ].describe().T
                )


                statistics["median"] = (
                    cleaned_df[
                        numeric_columns
                    ].median()
                )


                statistics["missing"] = (
                    cleaned_df[
                        numeric_columns
                    ]
                    .isnull()
                    .sum()
                )


                statistics = statistics[
                    [
                        "count",
                        "mean",
                        "median",
                        "std",
                        "min",
                        "max",
                        "missing"
                    ]
                ]


                st.dataframe(
                    statistics.round(2),
                    use_container_width=True
                )

            else:

                st.info(
                    "No numerical columns detected."
                )


            if len(numeric_columns) >= 2:

                st.subheader(
                    "🔗 Correlation Analysis"
                )


                correlation = (
                    cleaned_df[
                        numeric_columns
                    ].corr()
                )


                st.dataframe(
                    correlation.round(2),
                    use_container_width=True
                )


            st.divider()


            st.header(
                "🎯 Automatic KPI Detection"
            )


            kpi_candidates = []


            for column in numeric_columns:

                series = (
                    cleaned_df[
                        column
                    ].dropna()
                )


                if len(series) == 0:
                    continue


                kpi_candidates.append(
                    {
                        "Metric": column,
                        "Total": series.sum(),
                        "Average": series.mean(),
                        "Minimum": series.min(),
                        "Maximum": series.max()
                    }
                )


            if kpi_candidates:

                kpi_df = pd.DataFrame(
                    kpi_candidates
                )


                st.dataframe(
                    kpi_df.round(2),
                    use_container_width=True
                )


                st.subheader(
                    "⭐ Key Metrics"
                )


                metric_count = min(
                    len(kpi_candidates),
                    4
                )


                metric_columns = st.columns(
                    metric_count
                )


                for i in range(
                    metric_count
                ):

                    metric = kpi_candidates[i]


                    with metric_columns[i]:

                        st.metric(
                            metric["Metric"],
                            f"{metric['Total']:,.2f}"
                        )

            else:

                st.info(
                    "No numerical metrics detected."
                )


            st.divider()


            st.header(
                "📊 Automatic Visualizations"
            )


            if numeric_columns:

                st.subheader(
                    "📈 Numerical Distribution"
                )


                selected_numeric = st.selectbox(
                    "Select a numerical column",
                    numeric_columns,
                    key="distribution_column"
                )


                fig = px.histogram(
                    cleaned_df,
                    x=selected_numeric,
                    title=(
                        f"Distribution of "
                        f"{selected_numeric}"
                    ),
                    marginal="box"
                )


                st.plotly_chart(
                    fig,
                    use_container_width=True
                )


            if categorical_columns:

                st.subheader(
                    "📊 Basic Category Analysis"
                )


                selected_category = st.selectbox(
                    "Select a categorical column",
                    categorical_columns,
                    key="category_column"
                )


                category_counts_basic = (
                    cleaned_df[
                        selected_category
                    ]
                    .value_counts()
                    .head(15)
                    .reset_index()
                )


                category_counts_basic.columns = [
                    selected_category,
                    "Count"
                ]


                fig = px.bar(
                    category_counts_basic,
                    x=selected_category,
                    y="Count",
                    title=(
                        f"Top Categories — "
                        f"{selected_category}"
                    )
                )


                st.plotly_chart(
                    fig,
                    use_container_width=True
                )


            if len(numeric_columns) >= 2:

                st.subheader(
                    "🔵 Relationship Analysis"
                )


                x_column = st.selectbox(
                    "X-axis",
                    numeric_columns,
                    key="x_column"
                )


                y_options = [
                    column
                    for column in numeric_columns
                    if column != x_column
                ]


                if y_options:

                    y_column = st.selectbox(
                        "Y-axis",
                        y_options,
                        key="y_column"
                    )


                    fig = px.scatter(
                        cleaned_df,
                        x=x_column,
                        y=y_column,
                        title=(
                            f"{x_column} vs "
                            f"{y_column}"
                        )
                    )


                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )


            st.divider()


            st.header(
                "📅 Automatic Date & Time Analysis"
            )


            date_columns = detect_date_columns(
                cleaned_df
            )


            if date_columns:

                st.success(
                    f"Detected {len(date_columns)} date column(s)."
                )


                selected_date_column = st.selectbox(
                    "Select Date Column",
                    date_columns,
                    key="date_column"
                )


                date_summary = get_date_summary(
                    cleaned_df,
                    selected_date_column
                )


                if date_summary:

                    d1, d2, d3, d4 = st.columns(4)


                    with d1:

                        st.metric(
                            "Earliest Date",
                            date_summary[
                                "earliest_date"
                            ].strftime(
                                "%Y-%m-%d"
                            )
                        )


                    with d2:

                        st.metric(
                            "Latest Date",
                            date_summary[
                                "latest_date"
                            ].strftime(
                                "%Y-%m-%d"
                            )
                        )


                    with d3:

                        st.metric(
                            "Date Range",
                            f"{date_summary['days']:,} days"
                        )


                    with d4:

                        st.metric(
                            "Valid Date Records",
                            f"{date_summary['records']:,}"
                        )


                    if numeric_columns:

                        st.subheader(
                            "📈 Monthly Trend"
                        )


                        selected_value_column = (
                            st.selectbox(
                                "Select Metric",
                                numeric_columns,
                                key="date_value_column"
                            )
                        )


                        monthly_data = (
                            monthly_summary(
                                cleaned_df,
                                selected_date_column,
                                selected_value_column
                            )
                        )


                        if (
                            monthly_data is not None
                            and not monthly_data.empty
                        ):

                            fig = px.line(
                                monthly_data,
                                x="Month",
                                y=selected_value_column,
                                markers=True,
                                title=(
                                    f"Monthly "
                                    f"{selected_value_column}"
                                )
                            )


                            st.plotly_chart(
                                fig,
                                use_container_width=True
                            )

            else:

                st.info(
                    "No date columns were automatically detected."
                )


            st.divider()


            st.header(
                "🏷️ Automatic Categorical Analysis"
            )


            detected_categories = (
                get_categorical_columns(
                    cleaned_df
                )
            )


            if detected_categories:

                st.success(
                    f"Detected {len(detected_categories)} "
                    f"categorical column(s)."
                )


                selected_analysis_category = (
                    st.selectbox(
                        "Select Categorical Column",
                        detected_categories,
                        key="analysis_category_column"
                    )
                )


                st.subheader(
                    "📊 Category Distribution"
                )


                counts = category_counts(
                    cleaned_df,
                    selected_analysis_category
                )


                if (
                    counts is not None
                    and not counts.empty
                ):

                    fig = px.bar(
                        counts,
                        x=selected_analysis_category,
                        y="Count",
                        title=(
                            f"Top Categories — "
                            f"{selected_analysis_category}"
                        )
                    )


                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )


                    st.dataframe(
                        counts,
                        use_container_width=True
                    )


                if numeric_columns:

                    st.subheader(
                        "📈 Category Performance"
                    )


                    selected_metric = st.selectbox(
                        "Select Numeric Metric",
                        numeric_columns,
                        key="category_metric_column"
                    )


                    performance = (
                        category_metric_summary(
                            cleaned_df,
                            selected_analysis_category,
                            selected_metric
                        )
                    )


                    if (
                        performance is not None
                        and not performance.empty
                    ):

                        st.dataframe(
                            performance.round(2),
                            use_container_width=True
                        )


                        top_category = (
                            get_top_category(
                                cleaned_df,
                                selected_analysis_category,
                                selected_metric
                            )
                        )


                        bottom_category = (
                            get_bottom_category(
                                cleaned_df,
                                selected_analysis_category,
                                selected_metric
                            )
                        )


                        if top_category is not None:

                            st.success(
                                f"🏆 Top "
                                f"{selected_analysis_category}: "
                                f"{top_category[selected_analysis_category]} "
                                f"with total "
                                f"{selected_metric} of "
                                f"{top_category['Total']:,.2f}"
                            )


                        if bottom_category is not None:

                            st.info(
                                f"📉 Lowest "
                                f"{selected_analysis_category}: "
                                f"{bottom_category[selected_analysis_category]} "
                                f"with total "
                                f"{selected_metric} of "
                                f"{bottom_category['Total']:,.2f}"
                            )


                        performance_chart = px.bar(
                            performance.head(15),
                            x=selected_analysis_category,
                            y="Total",
                            title=(
                                f"{selected_metric} by "
                                f"{selected_analysis_category}"
                            )
                        )


                        st.plotly_chart(
                            performance_chart,
                            use_container_width=True
                        )

            else:

                st.info(
                    "No categorical columns were detected."
                )


            st.divider()


            st.header(
                "🔍 Advanced Dataset Profile"
            )


            dataset_profile = profile_dataset(
                cleaned_df
            )


            ai_context = create_ai_context(
                dataset_profile
            )


            st.success(
                "✅ Dataset profile generated successfully."
            )


            with st.expander(
                "🔎 View Dataset Profile"
            ):

                st.json(
                    dataset_profile
                )


            st.divider()


            dataset_summary = {

                "rows": len(cleaned_df),

                "columns": len(
                    cleaned_df.columns
                ),

                "column_names": (
                    cleaned_df.columns.tolist()
                ),

                "numeric_columns": (
                    numeric_columns
                ),

                "categorical_columns": (
                    categorical_columns
                ),

                "missing_values": int(
                    cleaned_df
                    .isnull()
                    .sum()
                    .sum()
                ),

                "duplicate_rows": int(
                    cleaned_df
                    .duplicated()
                    .sum()
                ),

                "statistics": (

                    cleaned_df[
                        numeric_columns
                    ]
                    .describe()
                    .round(2)
                    .to_dict()

                    if numeric_columns

                    else {}
                ),

                "advanced_profile": (
                    dataset_profile
                ),

                "ai_context": (
                    ai_context
                )
            }


            st.header(
                "💡 Automatic Business Insights"
            )


            st.write(
                "Let the AI identify important "
                "patterns and potential business insights."
            )


            if st.button(
                "💡 Generate Business Insights",
                use_container_width=True
            ):

                with st.spinner(
                    "AI is analyzing the dataset..."
                ):

                    insights = (
                        generate_business_insights(
                            dataset_summary
                        )
                    )


                st.success(
                    "Business insights generated successfully."
                )


                st.markdown(
                    insights
                )


            st.divider()


            st.header(
                "🤖 AI Data Analyst"
            )


            st.write(
                "Ask questions about the analyzed dataset."
            )


            question = st.text_area(
                "Ask the AI Analyst",
                placeholder=(
                    "Examples:\n"
                    "What is the total Sales?\n"
                    "What is the average Profit?\n"
                    "What are the biggest problems in this dataset?\n"
                    "Give me 5 important business insights.\n"
                    "What additional analysis should I perform?"
                )
            )


            if st.button(
                "🤖 Analyze",
                use_container_width=True
            ):

                if not question.strip():

                    st.warning(
                        "Please enter a question."
                    )

                else:

                    with st.spinner(
                        "Analyzing your question..."
                    ):

                        direct_answer = (
                            query_dataset(
                                cleaned_df,
                                question
                            )
                        )


                    if direct_answer:

                        st.subheader(
                            "📊 Data Result"
                        )


                        st.success(
                            direct_answer
                        )

                    else:

                        with st.spinner(
                            "AI is analyzing the dataset..."
                        ):

                            answer = (
                                generate_analysis(
                                    dataset_summary,
                                    question
                                )
                            )


                        st.subheader(
                            "🤖 AI Response"
                        )


                        st.write(
                            answer
                        )


            st.divider()


            st.header("🤖 Autonomous Analyst")
            st.write(
                "For complex questions, Qwen3 creates a constrained plan while "
                "registered Pandas tools perform every calculation."
            )

            with st.form("autonomous_analyst_form", border=True):
                autonomous_question = st.text_area(
                    "Business question",
                    placeholder="Which region has the highest profit and why?",
                    key="autonomous_analyst_question"
                )
                autonomous_submit = st.form_submit_button(
                    "Run controlled analysis",
                    type="primary"
                )

            if autonomous_submit:
                if not autonomous_question.strip():
                    st.warning("Enter a business question to start the analysis.")
                else:
                    with st.spinner("Planning and validating deterministic analysis..."):
                        try:
                            st.session_state["autonomous_analysis_result"] = (
                                run_autonomous_analysis(cleaned_df, autonomous_question)
                            )
                        except PlanValidationError as error:
                            st.session_state["autonomous_analysis_error"] = str(error)
                        except Exception as error:
                            st.session_state["autonomous_analysis_error"] = (
                                f"Controlled analysis could not complete: {error}"
                            )

            if "autonomous_analysis_error" in st.session_state:
                st.error(st.session_state.pop("autonomous_analysis_error"))

            autonomous_result = st.session_state.get("autonomous_analysis_result")
            if autonomous_result:
                st.subheader("Answer")
                st.markdown(autonomous_result["answer"])
                visualization = autonomous_result["visualization"]
                st.subheader("Recommended visualization")
                st.write(
                    f"**{visualization['chart_type'].replace('_', ' ').title()}** — "
                    f"{visualization['title']}"
                )
                st.caption(visualization.get("reason", ""))
                st.write("**Power BI:** " + visualization.get("power_bi", "Not applicable"))
                st.write("**Tableau:** " + visualization.get("tableau", "Not applicable"))
                if autonomous_result.get("plan"):
                    with st.expander("View analysis plan"):
                        st.json(autonomous_result["plan"])
                with st.expander("View evidence"):
                    st.json(autonomous_result["evidence"])
                with st.expander("View execution trace"):
                    st.dataframe(pd.DataFrame(autonomous_result["trace"]))


            st.divider()


            st.subheader(
                "📋 Cleaned Dataset Preview"
            )


            st.dataframe(
                cleaned_df.head(100),
                use_container_width=True
            )


    except Exception as e:

        st.error(
            f"Unable to process the dataset: {e}"
        )

else:

    st.info(
        "Upload a CSV or Excel dataset to get started."
    )
