import streamlit as st
import requests
import json
from datetime import datetime
import time

# Configuration
API_URL = "http://localhost:8000/api/v1/generate-mcq"

# Page configuration
st.set_page_config(
    page_title="MCQ Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .sidebar-content {
        padding: 1rem;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-left: 5px solid #28a745;
        background-color: #d4edda;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-left: 5px solid #17a2b8;
        background-color: #d1ecf1;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .stExpander > div > div > div > div {
        background-color: #f8f9fa;
    }
    .question-counter {
        background-color: #e3f2fd;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.5rem 0;
        font-weight: bold;
        color: #1976d2;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🎯 Smart MCQ Generator</h1>
    <p>Generate intelligent multiple-choice questions with smart insights</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'generation_history' not in st.session_state:
    st.session_state.generation_history = []

# Sidebar for form inputs
with st.sidebar:
    st.markdown("### 🔧 Configuration Panel")

    with st.form("mcq_form", clear_on_submit=False):
        st.markdown("#### 👤 User Information")
        username = st.text_input(
            "Username",
            value="speed_test",
            help="Enter your username for tracking"
        )

        st.markdown("#### 📚 Content Settings")
        topic = st.text_input(
            "Learning Topic",
            value="Python data types",
            help="Specify the topic for MCQ generation"
        )

        difficulty = st.selectbox(
            "Difficulty Level",
            ["basic", "intermediate", "advanced"],
            index=0,
            help="Choose appropriate difficulty level"
        )

        question_count = st.slider(
            "Number of Questions",
            min_value=1,
            max_value=20,
            value=10,
            help="Select how many questions to generate"
        )

        st.markdown("#### ⚡ Additional Features")
        col1, col2 = st.columns(2)
        with col1:
            include_roadmap = st.checkbox("📍 Learning Roadmap", True)
        with col2:
            include_videos = st.checkbox("🎥 Video Resources", True)

        st.markdown("---")
        submitted = st.form_submit_button(
            "🚀 Generate MCQs",
            use_container_width=True,
            type="primary"
        )

    # Generation history in sidebar
    if st.session_state.generation_history:
        st.markdown("### 📈 Recent Generations")
        for i, hist in enumerate(reversed(st.session_state.generation_history[-3:])):
            with st.expander(f"#{len(st.session_state.generation_history)-i}: {hist['topic'][:20]}..."):
                st.write(f"**Questions:** {hist['count']}")
                st.write(f"**Difficulty:** {hist['difficulty']}")
                st.write(f"**Time:** {hist['timestamp']}")

# Main content area
if submitted:
    # Validate inputs
    if not username.strip():
        st.error("⚠️ Please enter a username")
        st.stop()

    if not topic.strip():
        st.error("⚠️ Please enter a topic")
        st.stop()

    # Prepare payload
    payload = {
        "username": username.strip(),
        "topic": topic.strip(),
        "difficulty": difficulty,
        "question_count": question_count,
        "include_roadmap": include_roadmap,
        "include_videos": include_videos,
    }

    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        with st.spinner("🔮 Generating intelligent MCQs..."):
            progress_bar.progress(25)
            status_text.text("Connecting to AI service...")

            start_time = time.time()
            response = requests.post(API_URL, json=payload, timeout=60)
            generation_time = time.time() - start_time

            progress_bar.progress(100)
            status_text.text("✅ Generation completed!")
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()

        if response.status_code == 200:
            data = response.json()
            st.session_state.generated_data = data

            # Add to history
            st.session_state.generation_history.append({
                'topic': topic,
                'count': question_count,
                'difficulty': difficulty,
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'generation_time': round(generation_time, 2)
            })

            # Success message
            st.success(f"✅ Successfully generated {question_count} MCQs in {generation_time:.2f} seconds!")

        else:
            st.error(f"❌ API Error: {response.status_code}")
            st.code(response.text, language="json")

    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        st.error("🔌 Connection error. Please check if the API server is running.")
    except Exception as e:
        st.error(f"🚨 Unexpected error: {str(e)}")

# Display generated content
if st.session_state.generated_data:
    data = st.session_state.generated_data

    # Create tabs for organized display
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🛤️ Learning Path", "🎥 Resources", "❓ Questions"])

    with tab1:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Generated Questions",
                len(data.get("questions", [])),
                help="Total number of MCQs generated"
            )

        with col2:
            st.metric(
                "Roadmap Steps",
                len(data.get("roadmap", [])),
                help="Learning roadmap milestones"
            )

        with col3:
            st.metric(
                "Video Resources",
                len(data.get("reference_videos", [])),
                help="Curated video materials"
            )

        # Metadata in expandable section
        if data.get("metadata"):
            with st.expander("🔍 Generation Metadata", expanded=False):
                st.json(data["metadata"])

    with tab2:
        if data.get("roadmap"):
            st.markdown("### 🛤️ Personalized Learning Roadmap")
            for i, step in enumerate(data["roadmap"]):
                with st.expander(
                    f"**Step {step['step_number']}: {step['title']}**",
                    expanded=(i == 0)
                ):
                    st.markdown(f"📝 **Description:** {step['description']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"⏱️ **Duration:** {step['estimated_duration']}")

                    if step.get("prerequisites"):
                        with col2:
                            st.warning(f"📋 **Prerequisites:** {', '.join(step['prerequisites'])}")
        else:
            st.info("🔄 No roadmap generated for this topic.")

    with tab3:
        if data.get("reference_videos"):
            st.markdown("### 🎥 Curated Video Resources")
            for vid in data["reference_videos"]:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**[{vid['title']}]({vid['url']})**")
                        st.caption(vid["description"])
                    with col2:
                        st.badge(vid['difficulty_level'])
                        st.caption(f"⏱️ {vid['duration']}")
                    st.divider()
        else:
            st.info("🔄 No video resources generated for this topic.")

    with tab4:
        if data.get("questions"):
            st.markdown("### 📝 Generated MCQs")

            # Question navigation
            total_questions = len(data["questions"])
            st.markdown(f"<div class='question-counter'>Total Questions: {total_questions}</div>", unsafe_allow_html=True)

            # Display questions with better formatting
            for i, q in enumerate(data["questions"]):
                with st.container():
                    st.markdown(f"### Question {q['question_id']}")
                    st.markdown(f"**{q['question_text']}**")

                    # Options in columns
                    cols = st.columns(2)
                    for j, opt in enumerate(q["options"]):
                        col_idx = j % 2
                        with cols[col_idx]:
                            if opt["is_correct"]:
                                st.success(f"✅ {opt['option']}")
                            else:
                                st.write(f"○ {opt['option']}")

                    # Explanation and metadata
                    with st.expander("💡 View Explanation & Details"):
                        st.info(f"**Explanation:** {q['explanation']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"🎯 **Difficulty:** {q['difficulty']}")
                        with col2:
                            st.caption(f"📚 **Topic Area:** {q['topic_area']}")

                    if i < total_questions - 1:
                        st.divider()
        else:
            st.warning("⚠️ No questions were generated. Please try again.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 1rem;'>"
    "🤖 Smart Technology • Built with Streamlit"
    "</div>",
    unsafe_allow_html=True
)
