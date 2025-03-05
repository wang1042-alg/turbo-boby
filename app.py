from flask import Flask, render_template, request
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# 设定时区
ottawa_tz = pytz.timezone("America/Toronto")
shanghai_tz = pytz.timezone("Asia/Shanghai")
brisbane_tz = pytz.timezone("Australia/Brisbane")

# 2025 年中国法定节假日
china_holidays_2025 = {
    "2025-01-01", "2025-02-29", "2025-03-01", "2025-03-02",
    "2025-04-05", "2025-05-01", "2025-06-10",
    "2025-09-15", "2025-10-01", "2025-10-02", "2025-10-03"
}

# 允许的时间段
TEACHER_AVAILABLE_START = 6  # 6:00 AM
TEACHER_AVAILABLE_END = 21  # 9:00 PM
STUDENT_AVAILABLE_START = 8  # 8:00 AM
STUDENT_AVAILABLE_END = 21  # 9:00 PM


def is_valid_class_time(teacher_time, selected_regions, student_start, student_end):
    """检查课程时间是否符合教师和学生的时间限制"""
    teacher_hour = teacher_time.hour + teacher_time.minute / 60
    student_time_shanghai = teacher_time.astimezone(shanghai_tz)
    student_hour_shanghai = student_time_shanghai.hour + student_time_shanghai.minute / 60
    student_time_brisbane = teacher_time.astimezone(brisbane_tz)
    student_hour_brisbane = student_time_brisbane.hour + student_time_brisbane.minute / 60

    # ✅ 确保教师时间符合范围
    if not (TEACHER_AVAILABLE_START <= teacher_hour <= TEACHER_AVAILABLE_END):
        return False

    # ✅ 确保学生时间符合范围（用户自定义）
    if "上海" in selected_regions and not (student_start <= student_hour_shanghai <= student_end):
        return False
    if "布里斯班" in selected_regions and not (student_start <= student_hour_brisbane <= student_end):
        return False

    return True



def generate_schedule(start_date_str, total_lessons, weekly_frequency, lesson_duration, selected_regions, teacher_start, student_start, student_end):
    """生成符合条件的课程表"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    start_time = datetime(start_date.year, start_date.month, start_date.day, teacher_start, 0)
    start_time = ottawa_tz.localize(start_time)

    lesson_interval_days = round(7 / weekly_frequency)
    lesson_dates = []
    current_time = start_time
    skipped_count = 0

    while len(lesson_dates) < total_lessons:
        date_str = current_time.strftime("%Y-%m-%d")

        if current_time.year > 2100:  
            print("❌ 课程安排超出允许范围，停止生成")
            return lesson_dates, "❌ 课程安排超出允许范围，未能成功安排课程，请调整时间后重试。"

        if date_str not in china_holidays_2025:
            if is_valid_class_time(current_time, selected_regions, student_start, student_end):
                lesson_dates.append(current_time)
                skipped_count = 0
            else:
                skipped_count += 1

        if skipped_count > 30:
            print("❌ 已连续 30 天找不到合适的课程时间，停止安排")
            return lesson_dates, "❌ 已连续 30 天找不到合适的课程时间，请调整可用时间或上课频率。"

        try:
            current_time += timedelta(days=lesson_interval_days)
        except OverflowError:
            return lesson_dates, "❌ 日期超出范围，课程安排失败，请调整时间设置。"

    return lesson_dates, None  # ✅ 成功安排课程，返回 None 代表没有错误





@app.route("/", methods=["GET", "POST"])
def index():
    lesson_dates = []
    lesson_shanghai = []
    lesson_brisbane = []
    error_message = None  # ✅ 新增错误消息变量

    show_shanghai = False
    show_brisbane = False

    start_date = None
    total_lessons = None
    weekly_frequency = None
    lesson_duration = None
    selected_regions = []

    teacher_start = int(request.form.get("teacher_start", 6))
    teacher_end = int(request.form.get("teacher_end", 21))
    student_start = int(request.form.get("student_start", 8))
    student_end = int(request.form.get("student_end", 21))

    if request.method == "POST":
        start_date = request.form.get("start_date")
        total_lessons = request.form.get("total_lessons")
        weekly_frequency = request.form.get("weekly_frequency")
        lesson_duration = request.form.get("lesson_duration")
        selected_regions = request.form.getlist("selected_regions")

        show_shanghai = "上海" in selected_regions
        show_brisbane = "布里斯班" in selected_regions

        lesson_dates, error_message = generate_schedule(
            start_date,
            int(total_lessons),
            int(weekly_frequency),
            float(lesson_duration),
            selected_regions,
            teacher_start,
            student_start,
            student_end
        )

        for lesson in lesson_dates:
            if show_shanghai:
                lesson_shanghai.append(lesson.astimezone(shanghai_tz).strftime('%Y-%m-%d %H:%M'))
            if show_brisbane:
                lesson_brisbane.append(lesson.astimezone(brisbane_tz).strftime('%Y-%m-%d %H:%M'))

    return render_template(
        "index.html",
        lesson_dates=lesson_dates,
        lesson_shanghai=lesson_shanghai,
        lesson_brisbane=lesson_brisbane,
        show_shanghai=show_shanghai,
        show_brisbane=show_brisbane,
        start_date=start_date,
        total_lessons=total_lessons,
        weekly_frequency=weekly_frequency,
        lesson_duration=lesson_duration,
        selected_regions=selected_regions,
        teacher_start=teacher_start,
        teacher_end=teacher_end,
        student_start=student_start,
        student_end=student_end,
        error_message=error_message  # ✅ 传递错误信息
    )




if __name__ == "__main__":
    app.run(debug=True)
