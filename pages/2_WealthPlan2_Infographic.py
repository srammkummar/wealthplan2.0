"""Full-size WealthPlan2.0 architecture infographic."""

from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INFOGRAPHIC_PATH = PROJECT_ROOT / "docs" / "WealthPlan2.0.png"


def main() -> None:
    st.set_page_config(
        page_title="WealthPlan2.0 workflow",
        page_icon="🧭",
        layout="wide",
    )

    with st.sidebar:
        st.markdown("### WealthPlan resources")
        st.page_link("streamlit_app.py", label="Back to WealthPlan workspace")
        st.page_link(
            "pages/1_Technical_Demo.py",
            label="Watch technical demo · 4:46",
        )

    st.title("WealthPlan2.0 multi-agent workflow")
    st.caption(
        "Follow the flow from investor input through LangGraph supervision, "
        "specialist agents, shared state, human approval, and final outputs."
    )

    if not INFOGRAPHIC_PATH.exists():
        st.error("The WealthPlan2.0 infographic is not available in this build.")
        st.stop()

    st.image(
        str(INFOGRAPHIC_PATH),
        caption="WealthPlan2.0: Multi-Agent Financial Research & Planning",
        use_container_width=True,
    )

    with INFOGRAPHIC_PATH.open("rb") as infographic:
        st.download_button(
            "Download infographic",
            data=infographic,
            file_name="WealthPlan2.0.png",
            mime="image/png",
        )

    st.info(
        "Educational prototype only. Reads and deterministic calculations may "
        "run autonomously; saving an approved report requires a human decision."
    )


if __name__ == "__main__":
    main()
