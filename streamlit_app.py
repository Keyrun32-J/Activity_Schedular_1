
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from pymongo import MongoClient
import pytz

# MongoDB Setup
client = MongoClient("mongodb+srv://society_user:Bank%401980@cluster0.sy8c2a5.mongodb.net/?retryWrites=true&w=majority")
db = client["task_scheduler_db"]
collection = db["tasks"]

# Slot Definitions
SLOTS = {
    "6:00 am - 9:00 am": (time(6, 0), time(9, 0)),
    "9:30 am - 12:30 pm": (time(9, 30), time(12, 30)),
    "1:00 pm - 4:00 pm": (time(13, 0), time(16, 0)),
    "4:30 pm - 7:30 pm": (time(16, 30), time(19, 30)),
    "8:00 pm - 10:00 pm": (time(20, 0), time(22, 0))
}

def get_slot(task_time):
    for slot, (start, end) in SLOTS.items():
        if start <= task_time <= end:
            return slot
    return "Other"

def load_tasks(date):
    tasks = list(collection.find({"date": date.strftime("%Y-%m-%d")}))
    df = pd.DataFrame(tasks)
    if not df.empty:
        df["Time"] = pd.to_datetime(df["time"], format="%H:%M").dt.time
        df["Slot"] = df["Time"].apply(get_slot)
        df["Datetime"] = pd.to_datetime(df["date"] + " " + df["time"])
    return df

def save_task(task_name, task_date, task_time, status):
    collection.insert_one({
        "task": task_name,
        "date": task_date.strftime("%Y-%m-%d"),
        "time": task_time.strftime("%H:%M"),
        "status": status
    })

def update_task_status(task_id, new_status):
    collection.update_one({"_id": task_id}, {"$set": {"status": new_status}})
    if new_status == "Push to Tomorrow":
        task = collection.find_one({"_id": task_id})
        new_date = datetime.strptime(task["date"], "%Y-%m-%d") + timedelta(days=1)
        collection.update_one({"_id": task_id}, {"$set": {"date": new_date.strftime("%Y-%m-%d"), "status": "Pending"}})

def delete_task(task_id):
    collection.delete_one({"_id": task_id})

st.set_page_config(page_title="📋 Task Scheduler", layout="wide")
st.title("📋 Daily Task Scheduler with Slots")

selected_date = st.date_input("📅 Select Date", value=datetime.now(pytz.timezone("Asia/Kolkata")).date())
task_filter = st.text_input("🔍 Search Task")

with st.form("add_task_form"):
    st.subheader("➕ Add a New Task")
    task_name = st.text_input("Task Name")
    task_time = st.time_input("Time")
    submitted = st.form_submit_button("Add Task")
    if submitted and task_name:
        save_task(task_name, selected_date, task_time, "Pending")
        st.success("Task added successfully!")

# Load and Filter Tasks
df = load_tasks(selected_date)
if not df.empty:
    if task_filter:
        df = df[df["task"].str.contains(task_filter, case=False)]

    # Summary Section
    st.subheader("📊 Task Summary")
    status_counts = df["status"].value_counts().to_dict()
    summary_cols = st.columns(4)
    summary_map = {
        "Completed": "✅",
        "In-Progress": "⏳",
        "Pending": "📅",
        "Push to Tomorrow": "⏭️"
    }
    for i, (status, icon) in enumerate(summary_map.items()):
        count = status_counts.get(status, 0)
        summary_cols[i].metric(label=f"{icon} {status}", value=str(count))

    st.markdown("---")

    # Task Table by Slot
    st.subheader("🗂️ Task List")
    for slot in SLOTS.keys():
        slot_df = df[df["Slot"] == slot]
        if not slot_df.empty:
            st.markdown(f"### 🕒 {slot}")
            for _, row in slot_df.iterrows():
                col1, col2, col3 = st.columns([6, 3, 1])
                with col1:
                    st.markdown(f"- **{row['task']}** ({row['time']})")
                with col2:
                    new_status = st.selectbox(
                        "Update Status",
                        ["Pending", "In-Progress", "Completed", "Push to Tomorrow", "Delete"],
                        index=["Pending", "In-Progress", "Completed", "Push to Tomorrow", "Delete"].index(row["status"]),
                        key=str(row["_id"])
                    )
                with col3:
                    if st.button("✅ Apply", key="btn_" + str(row["_id"])):
                        if new_status == "Delete":
                            delete_task(row["_id"])
                        else:
                            update_task_status(row["_id"], new_status)
                        st.rerun()
else:
    st.info("No tasks for selected date.")
