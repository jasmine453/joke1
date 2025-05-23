import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random
from tkinter import font as tkfont
from PIL import Image, ImageTk
import os
import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify, redirect, url_for

# 板块列表（初始可为空，动态收集）
CATEGORIES = []

# 全局变量
current_joke = None
jokes = []

class JokeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("冷笑话")
        self.root.geometry("800x600")  # 调小窗口尺寸
        self.root.configure(bg='#E3F2FD')  # 冷色调蓝色背景
        self.style = ttk.Style()
        # 按钮字体颜色改为黑色
        self.style.configure('Custom.TButton', padding=10, font=('Microsoft YaHei', 11, 'bold'), background='#1976D2', foreground='#000000')
        self.style.map('Custom.TButton', foreground=[('active', '#1976D2')], background=[('active', '#90CAF9')])
        self.style.configure('Title.TLabel', font=('Microsoft YaHei', 20, 'bold'), padding=10, background='#E3F2FD')
        self.style.configure('Question.TLabel', font=('Microsoft YaHei', 14), padding=10, background='#E3F2FD')
        self.jokes = self.load_jokes()
        self.current_joke = None
        self.used_jokes = set()
        self.selected_category = tk.StringVar(value="混合")
        self.update_categories_from_jokes()
        # 贴图图片更换为用户新上传的抠图图片
        self.sticker_images = [
            "e8cd6a2c601f292e453fb2bc6d0d5a8.jpg",
            "b27cffc6f3497bf9cebc800d8b4c9c1.jpg",
            "35c3402b23713801b6eda8ccb27063a.jpg",
            "2b54fa51de6c057cfe8d063a117ffc9.jpg"
        ]
        # 只允许贴图在四角和底部两侧，避免遮挡主内容
        self.sticker_positions = [
            {'relx':0.01, 'rely':0.01, 'anchor':'nw'}, # 左上
            {'relx':0.99, 'rely':0.01, 'anchor':'ne'}, # 右上
            {'relx':0.01, 'rely':0.99, 'anchor':'sw'}, # 左下
            {'relx':0.99, 'rely':0.99, 'anchor':'se'}, # 右下
            {'relx':0.15, 'rely':0.99, 'anchor':'s'},  # 底部左侧
            {'relx':0.85, 'rely':0.99, 'anchor':'s'}   # 底部右侧
        ]
        self.current_sticker_label = None
        self.create_widgets()
        self.show_random_joke()

    def update_categories_from_jokes(self):
        global CATEGORIES
        cats = set(j['category'] for j in self.jokes if 'category' in j)
        CATEGORIES = sorted(list(cats - {"未分类"})) + (["未分类"] if "未分类" in cats else [])

    def load_jokes(self):
        try:
            with open('jokes.json', 'r', encoding='utf-8') as f:
                jokes = json.load(f)
                # 自动补充category字段
                for joke in jokes:
                    if 'category' not in joke:
                        for cat in CATEGORIES:
                            if cat in joke.get('explanation', ''):
                                joke['category'] = cat
                                break
                        else:
                            joke['category'] = '未分类'
                return jokes
        except FileNotFoundError:
            return []

    def save_jokes(self):
        with open('jokes.json', 'w', encoding='utf-8') as f:
            json.dump(self.jokes, f, ensure_ascii=False, indent=2)

    def calculate_similarity(self, text1, text2):
        words1 = set(jieba.cut(text1))
        words2 = set(jieba.cut(text2))
        common_words = words1.intersection(words2)
        if not words1 or not words2:
            return 0.0
        keyword_similarity = len(common_words) / max(len(words1), len(words2))
        words1_str = ' '.join(words1)
        words2_str = ' '.join(words2)
        vectorizer = TfidfVectorizer()
        try:
            tfidf_matrix = vectorizer.fit_transform([words1_str, words2_str])
            semantic_similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            semantic_similarity = 0.0
        final_similarity = 0.7 * keyword_similarity + 0.3 * semantic_similarity
        return final_similarity

    def get_all_categories(self):
        # 动态获取所有板块
        cats = set(j['category'] for j in self.jokes if 'category' in j)
        return ["混合"] + sorted(list(cats - {"未分类"})) + (["未分类"] if "未分类" in cats else [])

    def create_widgets(self):
        # 初始界面整体居中frame
        self.init_frame = ttk.Frame(self.root, style='Main.TFrame')
        self.init_frame.pack(expand=True, fill='both')
        self.init_title_label = ttk.Label(self.init_frame, text="冷笑话", font=('Microsoft YaHei', 36, 'bold'), background='#E3F2FD', anchor='center')
        self.init_title_label.pack(pady=(60, 30))
        category_frame = ttk.Frame(self.init_frame, style='Main.TFrame')
        category_frame.pack(pady=10)
        ttk.Label(category_frame, text="选择板块：", font=('Microsoft YaHei', 16), background='#E3F2FD').pack(side='left', padx=(0, 8))
        self.category_combobox = ttk.Combobox(category_frame, textvariable=self.selected_category, state='readonly', font=('Microsoft YaHei', 16))
        self.category_combobox['values'] = self.get_all_categories()
        self.category_combobox.current(0)
        self.category_combobox.pack(side='left')
        self.category_combobox.bind('<<ComboboxSelected>>', lambda e: self.show_main_content())
        # 主内容区（初始不pack）
        self.center_frame = ttk.Frame(self.root, style='Main.TFrame')
        self.main_frame = ttk.Frame(self.center_frame, padding="20", style='Main.TFrame')
        self.main_frame.pack(expand=True)
        self.main_content_widgets = []
        title_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        self.main_content_widgets.append(title_frame)
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        title_label = ttk.Label(title_frame, text="✨ 冷笑话 ✨", style='Title.TLabel')
        title_label.grid(row=0, column=1, pady=(0, 20))
        # 使用已有的图片文件
        left_image = self.create_rounded_image("e8cd6a2c601f292e453fb2bc6d0d5a8.jpg", (150, 150))
        left_label = ttk.Label(title_frame, image=left_image, style='Main.TFrame')
        left_label.image = left_image
        left_label.grid(row=0, column=0, padx=20)
        right_image = self.create_rounded_image("b27cffc6f3497bf9cebc800d8b4c9c1.jpg", (150, 150))
        right_label = ttk.Label(title_frame, image=right_image, style='Main.TFrame')
        right_label.image = right_image
        right_label.grid(row=0, column=2, padx=20)
        question_frame = ttk.Frame(self.main_frame, style='Card.TFrame')
        self.main_content_widgets.append(question_frame)
        question_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        self.question_label = ttk.Label(question_frame, text="", wraplength=800, style='Question.TLabel')
        self.question_label.grid(row=0, column=0, pady=20, padx=20)
        answer_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        self.main_content_widgets.append(answer_frame)
        answer_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        self.answer_var = tk.StringVar()
        self.answer_entry = ttk.Entry(answer_frame, textvariable=self.answer_var, width=70, font=('Microsoft YaHei', 12))
        self.answer_entry.grid(row=0, column=0, pady=10)
        button_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        self.main_content_widgets.append(button_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 20))
        submit_btn = ttk.Button(button_frame, text="✨ 提交答案", command=self.check_answer, style='Custom.TButton')
        submit_btn.grid(row=0, column=0, padx=10)
        next_btn = ttk.Button(button_frame, text="🎲 下一题", command=self.show_random_joke, style='Custom.TButton')
        next_btn.grid(row=0, column=1, padx=10)
        upload_btn = ttk.Button(button_frame, text="📝 上传笑话", command=self.show_upload_dialog, style='Custom.TButton')
        upload_btn.grid(row=0, column=2, padx=10)
        result_frame = ttk.Frame(self.main_frame, style='Card.TFrame')
        self.main_content_widgets.append(result_frame)
        result_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))
        self.result_text = tk.Text(result_frame, height=8, width=80, font=('Microsoft YaHei', 11), wrap=tk.WORD, bg='#E3F2FD')
        self.result_text.grid(row=0, column=0, pady=10)
        self.result_text.config(state='disabled')
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text.configure(yscrollcommand=scrollbar.set)
        self.answer_entry.bind('<Return>', lambda e: self.check_answer())
        self.style.configure('Main.TFrame', background='#E3F2FD')
        self.style.configure('Card.TFrame', background='#BBDEFB')
        self.show_sticker()
        # 初始隐藏主内容区
        self.center_frame.pack_forget()
        for w in self.main_content_widgets:
            w.grid_remove()

    def show_main_content(self):
        self.init_frame.pack_forget()
        self.center_frame.pack(expand=True, fill='both')
        for w in self.main_content_widgets:
            w.grid()
        self.reset_and_show()

    def reset_and_show(self):
        self.used_jokes.clear()
        self.show_random_joke()

    def create_rounded_image(self, image_path, size):
        try:
            image = Image.open(image_path)
            image = image.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except:
            image = Image.new('RGBA', size, (255, 245, 245, 0))
            return ImageTk.PhotoImage(image)

    def show_upload_dialog(self):
        upload_window = tk.Toplevel(self.root)
        upload_window.title("上传新笑话")
        upload_window.geometry("600x550")
        upload_window.configure(bg='#E3F2FD')
        input_frame = ttk.Frame(upload_window, padding="20", style='Main.TFrame')
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        title_label = ttk.Label(input_frame, text="✨ 上传新笑话 ✨", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        ttk.Label(input_frame, text="问题：", font=('Microsoft YaHei', 11)).grid(row=1, column=0, pady=5, sticky='w')
        question_entry = ttk.Entry(input_frame, width=50, font=('Microsoft YaHei', 11))
        question_entry.grid(row=1, column=1, pady=5, padx=5)
        ttk.Label(input_frame, text="答案：", font=('Microsoft YaHei', 11)).grid(row=2, column=0, pady=5, sticky='w')
        answer_entry = ttk.Entry(input_frame, width=50, font=('Microsoft YaHei', 11))
        answer_entry.grid(row=2, column=1, pady=5, padx=5)
        ttk.Label(input_frame, text="解释：", font=('Microsoft YaHei', 11)).grid(row=3, column=0, pady=5, sticky='w')
        explanation_text = tk.Text(input_frame, height=8, width=50, font=('Microsoft YaHei', 11))
        explanation_text.grid(row=3, column=1, pady=5, padx=5)
        # 板块选择，允许输入新板块
        ttk.Label(input_frame, text="板块分类：", font=('Microsoft YaHei', 11)).grid(row=4, column=0, pady=5, sticky='w')
        category_var = tk.StringVar(value=CATEGORIES[0] if CATEGORIES else "")
        category_combobox = ttk.Combobox(input_frame, textvariable=category_var, state='normal', font=('Microsoft YaHei', 11))
        category_combobox['values'] = CATEGORIES
        category_combobox.grid(row=4, column=1, pady=5, padx=5)
        def save_joke():
            question = question_entry.get().strip()
            answer = answer_entry.get().strip()
            explanation = explanation_text.get("1.0", tk.END).strip()
            category = category_var.get().strip()
            if not question or not answer:
                messagebox.showwarning("警告", "问题和答案不能为空！")
                return
            if not category:
                messagebox.showwarning("警告", "板块分类不能为空！")
                return
            new_joke = {
                'id': len(self.jokes) + 1,
                'question': question,
                'answer': answer,
                'explanation': explanation,
                'category': category
            }
            self.jokes.append(new_joke)
            self.save_jokes()
            # 动态添加新板块
            if category not in CATEGORIES:
                CATEGORIES.append(category)
                CATEGORIES.sort()
            self.category_combobox['values'] = self.get_all_categories()
            messagebox.showinfo("成功", "笑话上传成功！")
            upload_window.destroy()
        save_btn = ttk.Button(input_frame, text="✨ 保存", command=save_joke, style='Custom.TButton')
        save_btn.grid(row=5, column=0, columnspan=2, pady=20)

    def show_sticker(self):
        if self.current_sticker_label:
            self.current_sticker_label.destroy()
        img_path = random.choice(self.sticker_images)
        pos = random.choice(self.sticker_positions)
        try:
            img = Image.open(img_path)
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            tkimg = ImageTk.PhotoImage(img)
            label = tk.Label(self.root, image=tkimg, bg='#E3F2FD', borderwidth=0, highlightthickness=0)
            label.image = tkimg
            label.place(relx=pos['relx'], rely=pos['rely'], anchor=pos['anchor'])
            self.current_sticker_label = label
        except Exception as e:
            self.current_sticker_label = None

    def show_random_joke(self):
        if not self.jokes:
            messagebox.showwarning("警告", "没有可用的笑话！")
            return
        selected = self.selected_category.get()
        if selected == "混合":
            jokes_pool = self.jokes
        else:
            jokes_pool = [j for j in self.jokes if j.get('category') == selected]
        if not jokes_pool:
            messagebox.showwarning("警告", f"当前板块（{selected}）没有可用的笑话！")
            return
        if len(self.used_jokes) >= len(jokes_pool):
            messagebox.showinfo("提示", "本题库已全部使用！请重新选择板块。")
            self.used_jokes.clear()
            # 跳转回初始界面（只显示板块选择区，隐藏主内容区）
            for w in self.main_content_widgets:
                w.grid_remove()
            self.center_frame.pack_forget()
            self.init_frame.pack(expand=True, fill='both')
            return
        available_jokes = [j for j in jokes_pool if j['id'] not in self.used_jokes]
        self.current_joke = random.choice(available_jokes)
        self.used_jokes.add(self.current_joke['id'])
        self.question_label.config(text=self.current_joke['question'])
        self.answer_var.set("")
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state='disabled')
        self.show_sticker()

    def check_answer(self):
        if not self.current_joke:
            return
        user_answer = self.answer_var.get().strip()
        if not user_answer:
            messagebox.showwarning("警告", "请输入答案！")
            return
        similarity = self.calculate_similarity(user_answer, self.current_joke['answer'])
        is_correct = similarity > 0.3
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        if is_correct:
            self.result_text.insert(tk.END, "🎉 回答正确！\n\n")
        else:
            self.result_text.insert(tk.END, "❌ 回答不正确\n\n")
        self.result_text.insert(tk.END, f"📝 正确答案：{self.current_joke['answer']}\n\n")
        self.result_text.insert(tk.END, f"💡 解释：{self.current_joke['explanation']}\n\n")
        self.result_text.insert(tk.END, f"🔍 相似度：{similarity:.2%}")
        self.result_text.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    app = JokeApp(root)
    root.mainloop()



