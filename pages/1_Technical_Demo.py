"""Embedded technical-demo video for the WealthPlan Streamlit application."""

from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIDEO_PATH = PROJECT_ROOT / "assets" / "demos" / "wealthplan-technical-demo.mp4"
SUBTITLE_PATH = PROJECT_ROOT / "assets" / "demos" / "wealthplan-technical-demo.vtt"
TRANSCRIPT_PATH = PROJECT_ROOT / "docs" / "technical_demo_script.md"


def main() -> None:
    st.set_page_config(
        page_title="WealthPlan technical demo",
        page_icon="🎬",
        layout="wide",
    )
    with st.sidebar:
        st.markdown("### WealthPlan demos")
        st.caption("Use the page navigation above to return to the workspace.")

    st.title("How WealthPlan meets the Week 3 agent framework")
    st.caption(
        "A 4-minute 46-second full-screen guided walkthrough with female "
        "narration, visible cursor cues, and optional English captions."
    )

    if not VIDEO_PATH.exists():
        st.error("The technical-demo video is not available in this build.")
        st.stop()

    subtitles = SUBTITLE_PATH if SUBTITLE_PATH.exists() else None
    st.video(VIDEO_PATH, subtitles=subtitles)

    st.markdown("### What the video covers")
    chapters = [
        "Configure a real WealthPlan request in Streamlit",
        "Watch LangGraph supervision and parallel specialists execute",
        "Inspect SEC Company Facts and reranked Pinecone filing evidence",
        "Review deterministic portfolio and retirement calculations",
        "See checkpoint memory and approved-history boundaries",
        "Exercise the edit loop and reject without a durable write",
        "Map the working application to the Week 3 framework",
    ]
    for chapter in chapters:
        st.markdown(f"- {chapter}")

    if TRANSCRIPT_PATH.exists():
        with st.expander("Read the complete transcript"):
            st.markdown(TRANSCRIPT_PATH.read_text(encoding="utf-8"))

    st.info(
        "Educational prototype only. The application uses historical SEC "
        "information and illustrative calculations; it does not execute trades."
    )


if __name__ == "__main__":
    main()
