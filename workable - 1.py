import dearpygui.dearpygui as dpg
import json
import os
import cv2
import threading  # 用于图片显示的异步处理

# 文件夹路径
folder_path = 'output_folder_1'  # JSON 文件夹路径
image_folder_path = 'image'  # 图片文件夹路径

# 获取文件夹中的所有 JSON 文件
json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]

# 当前问题和文件索引
current_question_index = 0
current_file_index = 0
data = None
radio_group_tag = "radio_group"
image_display_thread = None  # 用于图片显示的线程
stop_thread = False  # 控制线程终止的标志位

def display_image(image_file_path):
    """异步显示图片的函数"""
    global stop_thread
    window_name = "Survey Image"
    img = cv2.imread(image_file_path)

    if img is not None:
        # 设置窗口属性，确保窗口置顶
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

        cv2.imshow(window_name, img)
        cv2.waitKey(1)  # 刷新窗口，延迟设为 1 毫秒

        # 循环刷新窗口，避免用户关闭
        while not stop_thread:
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                # 如果窗口被关闭，重新打开
                cv2.imshow(window_name, img)
            cv2.waitKey(50)  # 设置一个较长的刷新时间来减少卡顿
    else:
        print(f"Image not found: {image_file_path}")

    # 当标志位为 True 时，终止线程并关闭窗口
    cv2.destroyWindow(window_name)


def load_next_question():
    global current_question_index, current_file_index, data

    # 检查是否完成当前文件的所有问题
    if current_question_index >= len(data["questions"]):
        current_file_index += 1
        current_question_index = 0

        # 检查是否处理完所有文件
        if current_file_index >= len(json_files):
            dpg.set_value("question_text", "All questions from all files completed!")
            dpg.delete_item("submit_button")
            dpg.delete_item(radio_group_tag)
            return

        # 加载下一个 JSON 文件
        load_next_file()
        return  # 防止继续执行加载问题的逻辑

    # 获取当前问题数据
    question_data = data["questions"][current_question_index]

    # 更新类别和题干
    dpg.set_value("category_text", f"Category: {question_data['category']}")
    dpg.set_value("question_text", question_data["question"])
    dpg.set_value("answer_text", f"Answer: {question_data['answer']}")

    # 删除旧的选项
    for item in dpg.get_item_children(radio_group_tag, 1):
        dpg.delete_item(item)

    # 创建新的选项，添加"No problem"选项
    choices = ["No problem"] + [f"{key}: {choice}" for key, choice in question_data["choices"].items()]
    dpg.add_radio_button(items=choices, parent=radio_group_tag, default_value=choices[0], callback=record_answer)

def record_answer(sender, app_data):
    global current_file_index, current_question_index

    # 获取所选的答案
    selected_answer = app_data

    # 获取当前处理的文件名
    current_file_name = json_files[current_file_index]
    question_number = current_question_index + 1  # 题号从1开始

    # 只记录除"No problem"外的答案
    if selected_answer != "No problem":
        with open("output.txt", "a", encoding='utf-8') as f:
            f.write(f"File: {current_file_name}, Question: {question_number}, Answer: {selected_answer}\n")

def submit_answer(sender, app_data):
    global current_question_index
    # 直接加载下一个问题
    current_question_index += 1
    load_next_question()

def load_next_file():
    global data, current_file_index, current_question_index, image_display_thread, stop_thread

    # 读取当前 JSON 文件
    json_file_path = os.path.join(folder_path, json_files[current_file_index])
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 更新对话
    dpg.delete_item("dialogue_group", children_only=True)
    for dialogue in data.get("dialogue", []):  # 使用get方法防止KeyError
        dpg.add_text(f'{dialogue["speaker"]}: {dialogue["text"]}', parent="dialogue_group")

    # 终止上一个线程并销毁窗口
    if image_display_thread is not None:
        stop_thread = True  # 让上一个显示线程停止
        image_display_thread.join()  # 等待线程安全结束
        stop_thread = False  # 重置标志位

    # 加载对应的图片
    image_file_path = os.path.join(image_folder_path, json_files[current_file_index].replace('.json', '.jpg'))

    # 启动一个新的线程异步显示图片
    image_display_thread = threading.Thread(target=display_image, args=(image_file_path,))
    image_display_thread.start()

    # 加载第一个问题
    current_question_index = 0
    load_next_question()

def on_exit():
    """程序关闭时执行的操作"""
    global stop_thread, image_display_thread

    # 停止图片显示线程
    stop_thread = True
    if image_display_thread is not None:
        image_display_thread.join()

    # 关闭 OpenCV 窗口
    cv2.destroyAllWindows()
    print("Program exited cleanly.")

def create_gui():
    dpg.create_context()

    with dpg.window(label="Survey", width=1400, height=600):
        # 对话框部分
        with dpg.group(tag="dialogue_group"):
            pass  # 将在运行时动态添加对话

        dpg.add_spacer(height=10)

        # 显示题目的类别
        dpg.add_text("Category", tag="category_text")

        # 显示题目
        dpg.add_text("Question", tag="question_text")

        # 显示答案
        dpg.add_text("Answer", tag="answer_text", wrap=600)

        # 创建选项区域的容器
        dpg.add_group(tag=radio_group_tag)

        # 提交按钮
        dpg.add_button(label="Submit", callback=submit_answer, tag="submit_button")

        dpg.add_spacer(height=10)

        # 添加背景知识文本
        dpg.add_text("Background Knowledge:", bullet=True)
        dpg.add_text("1. Law of Attraction: The idea that positive or negative thoughts bring corresponding experiences into a person’s life.")
        dpg.add_text("2. Empathy Theory: The ability to understand and share the feelings of others, which helps create emotional connections.")
        dpg.add_text("3. Social Exchange Theory: A theory that explains relationships as a series of interactions where people balance costs and benefits.")

    # 设置窗口关闭回调
    dpg.set_exit_callback(on_exit)

    # 加载第一个文件
    load_next_file()

    dpg.create_viewport(title='Survey App', width=1000, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

# 启动GUI
create_gui()
