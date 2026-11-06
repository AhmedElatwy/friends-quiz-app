import flet as ft
import random
import json
import os
import csv
import io
import urllib.request

# مسار الحفظ الدائم (يعمل على الموبايل والكمبيوتر)
STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA", ".")
os.makedirs(STORAGE_DIR, exist_ok=True)
DATA_FILE = os.path.join(STORAGE_DIR, "game_data.json")
BASE_CATEGORIES = ["الكل", "دين", "تاريخ", "جغرافيا", "علوم", "عامة", "رياضة", "فن وثقافة"]
GOOGLE_SHEET_ID = "1qB1l9FtL8rtzlzXne5sBbFShuAkfSpKgh2jM4W3Yc0o"

# مسار بنك الأسئلة الأولي المدمج مع الكود
INITIAL_BANK_FILE = os.path.join(os.path.dirname(__file__), "initial_questions.json")

def main(page: ft.Page):
    # إعدادات الصفحة الأساسية
    page.title = "لعبة الأسئلة مع الأصحاب"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15
    try:
        page.window.width = 420
        page.window.height = 780
    except Exception:
        pass

    # دالة ذكية لإنشاء الأزرار تتوافق مع Flet 1.0 و 0.25+ بدون أخطاء
    def make_btn(label, on_click, icon=None, bgcolor=None, color=None, width=None):
        BtnClass = getattr(ft, "FilledButton", getattr(ft, "Button", None))
        try:
            return BtnClass(
                label,
                icon=icon,
                on_click=on_click,
                bgcolor=bgcolor,
                color=color,
                width=width
            )
        except TypeError:
            return BtnClass(
                content=ft.Text(label, color=color),
                icon=icon,
                on_click=on_click,
                width=width
            )

    # ---------------- إدارة حفظ وتحميل البيانات (JSON) ----------------
    default_data = {
        "players": [
            {"name": "أحمد", "score": 0},
            {"name": "محمد", "score": 0}
        ],
        "questions": [
          {"q": "ما هو الكوكب الذي يُسمى بالكوكب الأحمر؟", "a": "المريخ", "category": "علوم", "used": False},
          {"q": "كم عدد لاعبي فريق كرة القدم داخل الملعب؟", "a": "11 لاعب", "category": "رياضة", "used": False},
          {"q": "ما هي أكبر قارة في العالم من حيث المساحة؟", "a": "آسيا", "category": "جغرافيا", "used": False}
      ],
        "target_score": 5
    }

    def load_data():
        # 1. إذا كان ملف اللعبة محفوظاً مسبقاً على الجهاز، اقرأ منه
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # 2. عند فتح التطبيق لأول مرة، اسحب الأسئلة الضخمة من initial_questions.json
        initial_questions = default_data["questions"]
        if os.path.exists(INITIAL_BANK_FILE):
            try:
                with open(INITIAL_BANK_FILE, "r", encoding="utf-8") as f:
                    loaded_q = json.load(f)
                    if isinstance(loaded_q, list) and len(loaded_q) > 0:
                        initial_questions = loaded_q
            except Exception:
                pass

        return {
            "players": default_data["players"],
            "questions": initial_questions,
            "target_score": 5
        }

    game_data = load_data()
    players = game_data.get("players", default_data["players"])
    questions = game_data.get("questions", default_data["questions"])
    target_score = game_data.get("target_score", 5)

    def save_data():
        data_to_save = {
            "players": players,
            "questions": questions,
            "target_score": target_score
        }
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as ex:
            print("Error saving data:", ex)

    current_question = {"q": "اضغط على 'سؤال جديد' لبدء اللعب!", "a": ""}

    def notify(msg):
        sb = ft.SnackBar(ft.Text(msg))
        try:
            page.open(sb)
        except Exception:
            page.snack_bar = sb
            sb.open = True
            page.update()

    # =========================================================================
    # 1. عناصر ومنطق شاشة اللعب (Game Arena)
    # =========================================================================
    def get_available_categories():
        cats = list(BASE_CATEGORIES)
        for q in questions:
            c = q.get("category", "عامة").strip()
            if c and c not in cats:
                cats.append(c)
        return cats

    category_dropdown = ft.Dropdown(
        label="اختر تصنيف السؤال",
        value="الكل",
        width=200,
        options=[ft.dropdown.Option(c) for c in get_available_categories()]
    )

    category_badge = ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=4),
        bgcolor=ft.Colors.TEAL_800,
        border_radius=12,
        visible=False,
        content=ft.Text("", size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
    )

    question_text = ft.Text(
        current_question["q"],
        size=20,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER
    )
    answer_text = ft.Text(
        "",
        size=18,
        color=ft.Colors.GREEN_400,
        weight=ft.FontWeight.BOLD,
        visible=False
    )
    target_badge = ft.Text(
        f"هدف الجولة: {target_score} نقاط",
        size=14,
        color=ft.Colors.AMBER_400,
        weight=ft.FontWeight.BOLD
    )
    players_play_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def pick_random_question(e=None):
        selected_cat = category_dropdown.value or "الكل"
        available = [
            i for i, q in enumerate(questions)
            if not q.get("used", False) and (selected_cat == "الكل" or q.get("category", "عامة") == selected_cat)
        ]
        if not available:
            question_text.value = f"انتهت الأسئلة المتاحة في قسم ({selected_cat})! غيّر التصنيف أو اضغط (إعادة تفعيل كل الأسئلة)."
            answer_text.visible = False
            category_badge.visible = False
        else:
            chosen_idx = random.choice(available)
            questions[chosen_idx]["used"] = True
            current_question["q"] = questions[chosen_idx]["q"]
            current_question["a"] = questions[chosen_idx]["a"]
            q_cat = questions[chosen_idx].get("category", "عامة")

            question_text.value = current_question["q"]
            answer_text.value = f"الإجابة: {current_question['a']}"
            answer_text.visible = False
            category_badge.content.value = f"التصنيف: {q_cat}"
            category_badge.visible = True
            save_data()
        page.update()

    def show_answer(e):
        if current_question["a"]:
            answer_text.visible = not answer_text.visible
            page.update()

    def reset_questions_pool(e):
        for q in questions:
            q["used"] = False
        save_data()
        pick_random_question()
        notify("تم إعادة تفعيل جميع الأسئلة!")

    def reset_round_scores(e=None):
        for p in players:
            p["score"] = 0
        save_data()
        render_play_players()
        page.update()

    def show_winner_dialog(winner_name):
        def start_new_round(e):
            dialog.open = False
            reset_round_scores()
            pick_random_question()
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("🎉 مبروك الفوز بالجولة!", text_align=ft.TextAlign.CENTER),
            content=ft.Text(
                f"اللاعب ({winner_name}) وصل إلى {target_score} نقاط وفاز بالجولة!",
                size=18,
                text_align=ft.TextAlign.CENTER
            ),
            actions=[
                make_btn(
                    "بدء جولة جديدة",
                    on_click=start_new_round,
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        # الطريقة المضمونة لفتح الـ Dialog في Flet الحديث
        page.overlay.clear()
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def change_score(index, delta):
        players[index]["score"] += int(delta)
        save_data()
        render_play_players()
        # التأكد من المقارنة كأرقام صحيحة (int)
        if int(players[index]["score"]) >= int(target_score):
            show_winner_dialog(players[index]["name"])
        else:
            page.update()
            
    def render_play_players():
        players_play_column.controls.clear()
        target_badge.value = f"هدف الجولة: {target_score} نقاط"
        
        # إنشاء شبكة متجاوبة تقسم الصف إلى عمودين (كل بطاقة تأخذ 6 من 12)
        grid_row = ft.ResponsiveRow(spacing=8, run_spacing=8)
        
        for i, p in enumerate(players):
            card = ft.Card(
                col=6,  # 6 من 12 تعني عمودين في كل صف
                content=ft.Container(
                    padding=8,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Text(
                                p["name"],
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=4,
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.REMOVE_CIRCLE,
                                        icon_color=ft.Colors.RED_400,
                                        icon_size=26,
                                        on_click=lambda e, idx=i: change_score(idx, -1)
                                    ),
                                    ft.Container(
                                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                                        bgcolor=ft.Colors.BLUE_GREY_800,
                                        border_radius=8,
                                        content=ft.Text(str(p["score"]), size=18, weight=ft.FontWeight.BOLD)
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.ADD_CIRCLE,
                                        icon_color=ft.Colors.GREEN_400,
                                        icon_size=26,
                                        on_click=lambda e, idx=i: change_score(idx, 1)
                                    ),
                                ]
                            )
                        ]
                    )
                )
            )
            grid_row.controls.append(card)
            
        players_play_column.controls.append(grid_row)
    play_view = ft.Column(
        expand=True,
        controls=[
            ft.Row(
                [target_badge, make_btn("تصفير النقاط", on_click=reset_round_scores)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Card(
                elevation=4,
                content=ft.Container(
                    width=float("inf"),
                    padding=20,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row([category_dropdown, category_badge], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            question_text,
                            answer_text,
                            ft.Divider(),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[
                                    make_btn(
                                        "سؤال جديد",
                                        icon=ft.Icons.REFRESH,
                                        on_click=pick_random_question,
                                        bgcolor=ft.Colors.BLUE_700,
                                        color=ft.Colors.WHITE
                                    ),
                                    make_btn(
                                        "إظهار الإجابة",
                                        icon=ft.Icons.VISIBILITY,
                                        on_click=show_answer
                                    ),
                                ]
                            )
                        ]
                    )
                )
            ),
            ft.Text("قائمة اللاعبين:", size=16, weight=ft.FontWeight.BOLD),
            players_play_column,
            ft.Row(
                [make_btn("إعادة تفعيل كل الأسئلة", icon=ft.Icons.RESTORE, on_click=reset_questions_pool)],
                alignment=ft.MainAxisAlignment.CENTER
            )
        ]
    )

    # =========================================================================
    # 2. عناصر ومنطق شاشة إعداد اللاعبين والجولة (Setup Screen)
    # =========================================================================
    new_player_input = ft.TextField(label="اسم الصديق", expand=True)
    target_score_input = ft.TextField(
        label="نقاط الفوز في الجولة",
        value=str(target_score),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=160
    )
    setup_players_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    def add_player(e):
        name = new_player_input.value.strip()
        if name:
            players.append({"name": name, "score": 0})
            new_player_input.value = ""
            save_data()
            render_setup_players()
            render_play_players()
            page.update()

    def delete_player(index):
        players.pop(index)
        save_data()
        render_setup_players()
        render_play_players()
        page.update()

    def update_target_score(e):
        nonlocal target_score
        try:
            val = int(target_score_input.value)
            if val > 0:
                target_score = val
                save_data()
                render_play_players()
                notify(f"تم تحديد نقاط الفوز بـ {target_score} نقاط")
                page.update()
        except ValueError:
            pass

    def render_setup_players():
        setup_players_list.controls.clear()
        for i, p in enumerate(players):
            setup_players_list.controls.append(
                ft.Card(
                    content=ft.ListTile(
                        title=ft.Text(p["name"], weight=ft.FontWeight.BOLD),
                        trailing=ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED_400,
                            on_click=lambda e, idx=i: delete_player(idx)
                        )
                    )
                )
            )

    setup_view = ft.Column(
        expand=True,
        visible=False,
        controls=[
            ft.Text("إعدادات الجولة", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                target_score_input,
                make_btn("حفظ الهدف", icon=ft.Icons.CHECK, on_click=update_target_score)
            ]),
            ft.Divider(),
            ft.Text("إضافة اللاعبين", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                new_player_input,
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE,
                    icon_color=ft.Colors.BLUE_400,
                    icon_size=40,
                    on_click=add_player
                )
            ]),
            setup_players_list
        ]
    )

    # =========================================================================
    # 3. عناصر ومنطق شاشة بنك الأسئلة (Questions Bank)
    # =========================================================================
# =========================================================================
  # 3. عناصر ومنطق شاشة بنك الأسئلة + ربط Google Sheets
  # =========================================================================
    # ضع الـ ID الخاص بملف Google Sheets هنا بين علامتي التنصيص

    new_q_input = ft.TextField(label="اكتب السؤال هنا", multiline=True)
    new_a_input = ft.TextField(label="الإجابة الصحيحة", expand=True)
    new_cat_input = ft.Dropdown(
        label="التصنيف",
        value="عامة",
        width=130,
        options=[ft.dropdown.Option(c) for c in BASE_CATEGORIES if c != "الكل"]
    )
    questions_list_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    def refresh_category_dropdown():
        category_dropdown.options = [ft.dropdown.Option(c) for c in get_available_categories()]

    def add_question(e):
        q_val = new_q_input.value.strip()
        a_val = new_a_input.value.strip()
        cat_val = new_cat_input.value or "عامة"
        if q_val and a_val:
            questions.append({"q": q_val, "a": a_val, "category": cat_val, "used": False})
            new_q_input.value = ""
            new_a_input.value = ""
            save_data()
            refresh_category_dropdown()
            render_questions_bank()
            notify("تمت إضافة السؤال بنجاح!")
            page.update()

    def sync_from_google_sheets(e):
        if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID == "PUT_YOUR_GOOGLE_SHEET_ID_HERE":
            notify("يرجى وضع الـ ID الخاص بشيت جوجل في متغير GOOGLE_SHEET_ID أولاً!")
            return

        sheet_csv_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
        try:
            req = urllib.request.Request(sheet_csv_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                csv_text = response.read().decode('utf-8-sig')

            reader = csv.DictReader(io.StringIO(csv_text))
            existing_q_texts = {q["q"]: q for q in questions}
            added_count = 0
            updated_count = 0

            for row in reader:
                q_text = (row.get("q") or "").strip()
                a_text = (row.get("a") or "").strip()
                cat_text = (row.get("category") or "عامة").strip() or "عامة"

                if q_text and a_text:
                    if q_text not in existing_q_texts:
                        questions.append({
                            "q": q_text,
                            "a": a_text,
                            "category": cat_text,
                            "used": False
                        })
                        added_count += 1
                    else:
                        # تحديث الإجابة أو التصنيف لو عدلتها في الشيت
                        existing_q_texts[q_text]["a"] = a_text
                        existing_q_texts[q_text]["category"] = cat_text
                        updated_count += 1

            save_data()
            refresh_category_dropdown()
            render_questions_bank()
            notify(f"تم سحب {added_count} سؤال جديد وتحديث {updated_count} من Google Sheets!")
            page.update()
        except Exception as ex:
            notify("فشل الاتصال بالشيت! تأكد من جعل الشيت (أي شخص لديه الرابط) ومن اتصالك بالإنترنت.")

    def delete_question(index):
        questions.pop(index)
        save_data()
        refresh_category_dropdown()
        render_questions_bank()
        page.update()

    def render_questions_bank():
        questions_list_column.controls.clear()
        for i, q in enumerate(questions):
            cat_label = q.get("category", "عامة")
            questions_list_column.controls.append(
                ft.Card(
                    content=ft.ListTile(
                        title=ft.Text(f"[{cat_label}] {q['q']}"),
                        subtitle=ft.Text(f"الإجابة: {q['a']}", color=ft.Colors.GREEN_400),
                        trailing=ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED_400,
                            on_click=lambda e, idx=i: delete_question(idx)
                        )
                    )
                )
            )

    questions_view = ft.Column(
        expand=True,
        visible=False,
        controls=[
            ft.Text("إضافة سؤال جديد", size=20, weight=ft.FontWeight.BOLD),
            new_q_input,
            ft.Row([new_a_input, new_cat_input]),
            make_btn("إضافة لبنك الأسئلة", icon=ft.Icons.SAVE, on_click=add_question, width=float("inf")),
            make_btn(
                "تحديث الأسئلة من Google Sheets ☁️",
                icon=ft.Icons.CLOUD_SYNC,
                on_click=sync_from_google_sheets,
                bgcolor=ft.Colors.GREEN_800,
                color=ft.Colors.WHITE,
                width=float("inf")
            ),
            ft.Divider(),
            ft.Text(f"الأسئلة المضافة ({len(questions)}):", size=16, weight=ft.FontWeight.BOLD),
            questions_list_column
        ]
    )
    # =========================================================================
    # شريط التنقل السفلي (Navigation Bar)
    # =========================================================================
    def on_nav_change(e):
        idx = e.control.selected_index
        play_view.visible = (idx == 0)
        setup_view.visible = (idx == 1)
        questions_view.visible = (idx == 2)
        page.update()

    NavDest = getattr(ft, "NavigationBarDestination", getattr(ft, "NavigationDestination", None))
    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        destinations=[
            NavDest(icon=ft.Icons.SPORTS_ESPORTS, label="اللعب"),
            NavDest(icon=ft.Icons.PEOPLE, label="اللاعبين والجولة"),
            NavDest(icon=ft.Icons.QUIZ, label="بنك الأسئلة"),
        ]
    )

    # تهيئة الواجهات عند الفتح
    render_play_players()
    render_setup_players()
    render_questions_bank()

    page.add(play_view, setup_view, questions_view)

if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
