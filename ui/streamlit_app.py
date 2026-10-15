
import json
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Cynbit Discovery Intelligence",
    page_icon="🔎",
    layout="wide",
)

st.title("Cynbit Discovery Intelligence")
st.caption(
    "Turn unstructured client briefs into structured, "
    "evidence-backed discovery reports."
)

with st.sidebar:
    st.subheader("About")
    st.write(
        "Analyze client requirements, identify unknowns, "
        "and prepare focused discovery questions."
    )
    st.caption("AI-generated analysis requires human review.")

brief = st.text_area(
    "Client project brief",
    height=220,
    placeholder=(
        "Paste the client's project brief here...\n\n"
        "Example: We need an AI support assistant connected "
        "to our CRM. It should launch in four weeks."
    ),
)

if st.button("Analyze brief", type="primary"):
    if len(brief.strip()) < 20:
        st.warning("Please provide a brief of at least 20 characters.")
    else:
        try:
            with st.spinner("Analyzing the client brief..."):
                response = requests.post(
                    f"{API_URL}/analyze",
                    json={"brief": brief.strip()},
                    timeout=90,
                )
                response.raise_for_status()
                st.session_state["result"] = response.json()
                st.session_state["source_brief"] = brief.strip()

        except requests.RequestException as exc:
            st.error(
                "Could not complete the analysis. "
                "Check the API server and its logs."
            )
            # Avoid displaying request details that may expose internals.
            st.caption(f"Error type: {type(exc).__name__}")

result = st.session_state.get("result")

if result:
    st.divider()
    st.header("Discovery report")

    fields = [
        ("Project goal", "project_goal"),
        ("Target users", "target_users"),
        ("Integrations", "integrations"),
        ("Timeline", "timeline"),
        ("Budget", "budget"),
        ("Security requirements", "security_requirements"),
    ]

    for start in range(0, len(fields), 2):
        columns = st.columns(2)

        for column, (label, key) in zip(
            columns, fields[start:start + 2]
        ):
            item = result.get(key, {})

            with column:
                with st.container(border=True):
                    st.subheader(label)
                    st.write(item.get("value") or "Unknown")

                    status = item.get("status", "unknown")
                    st.caption(f"Status: {status}")

                    evidence = item.get("evidence", [])
                    if evidence:
                        st.markdown("**Source evidence**")
                        for quote in evidence:
                            st.markdown(f"> {quote}")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Missing information")
        missing = result.get("missing_information", [])

        if missing:
            for item in missing:
                st.markdown(f"- {item}")
        else:
            st.write("No missing fields reported.")

    with right:
        st.subheader("Potential risks")
        risks = result.get("potential_risks", [])

        if risks:
            for risk in risks:
                st.markdown(f"- {risk}")
        else:
            st.info("No risks were returned by the analysis.")

    st.divider()
    st.subheader("Discovery questions")

    questions = result.get("discovery_questions", [])

    if questions:
        for index, item in enumerate(questions, start=1):
            priority = item.get("priority", "medium").upper()
            st.markdown(
                f"**{index}. [{priority}]** "
                f"{item.get('question', '')}"
            )
    else:
        st.info("No discovery questions were returned.")

    st.download_button(
        "Download report as JSON",
        data=json.dumps(result, indent=2, ensure_ascii=False),
        file_name="discovery_report.json",
        mime="application/json",
    )

    with st.expander("View original brief"):
        st.write(st.session_state.get("source_brief", ""))
