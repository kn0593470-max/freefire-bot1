import os
import logging
import random
import sqlite3
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    ContextTypes, 
    CommandHandler, 
    CallbackQueryHandler
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8483501766:AAFSg-dWNLZjmKNQxMKQzZh2KOoyA_YBL5E"
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "@nhomsharemodallgame")
PORT = int(os.getenv("PORT", "8080"))
ADMIN_ID = 7907990385  # ID của riêng ông (Admin tối cao)

# --- KHỞI TẠO CƠ SỞ DỮ LIỆU SQLITE ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            xu INTEGER DEFAULT 0,
            joined INTEGER DEFAULT 0,
            has_been_referred INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT 0,
            reward_given INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            item_type TEXT PRIMARY KEY,
            quantity INTEGER
        )
    """)
    # Set số lượng mặc định ban đầu cho các loại kho
    cursor.execute("INSERT OR IGNORE INTO stock (item_type, quantity) VALUES ('huyen_thoai', 60)")
    cursor.execute("INSERT OR IGNORE INTO stock (item_type, quantity) VALUES ('clone30', 60)")
    cursor.execute("INSERT OR IGNORE INTO stock (item_type, quantity) VALUES ('clone58', 0)")
    conn.commit()
    conn.close()

init_db()

def get_stock(item_type):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM stock WHERE item_type = ?", (item_type,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def update_stock(item_type, amount):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    current = get_stock(item_type)
    new_qty = max(0, current + amount)
    cursor.execute("UPDATE stock SET quantity = ? WHERE item_type = ?", (new_qty, item_type))
    conn.commit()
    conn.close()
    return new_qty

def get_user(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT xu, joined, has_been_referred, referrer_id, reward_given FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, xu, joined) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        row = (0, 0, 0, 0, 0)
    conn.close()
    return {"xu": row[0], "joined": row[1], "has_been_referred": row[2], "referrer_id": row[3], "reward_given": row[4]}

def update_user_field(user_id, field, value):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def add_user_xu(user_id, amount):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT xu FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        new_xu = row[0] + amount
        cursor.execute("UPDATE users SET xu = ? WHERE user_id = ?", (new_xu, user_id))
    else:
        cursor.execute("INSERT INTO users (user_id, xu, joined) VALUES (?, ?, 0)", (user_id, amount))
    conn.commit()
    conn.close()

# Danh sách tài khoản mẫu
FAKE_ACCOUNTS_HUYEN_THOAI = [
    f"🏆 <b>ACC RANK HUYỀN THOẠI ({random.randint(1, 5)} SAO)</b>\n━━━━━━━━━━━━━━━━━━━\n📧 Tài khoản: <code>ht_pro_{random.randint(100,999)}@gmail.com</code>\n🔑 Mật khẩu: <code>huyenthoai2026</code>",
    f"🏆 <b>ACC RANK HUYỀN THOẠI ({random.randint(1, 5)} SAO)</b>\n━━━━━━━━━━━━━━━━━━━\n📧 Tài khoản: <code>legend_ff_{random.randint(100,999)}@gmail.com</code>\n🔑 Mật khẩu: <code>ffrankvip99</code>"
]

FAKE_ACCOUNTS_CLONE30 = [
    "💎 <b>ACC CLONE LEVEL 30</b>\n━━━━━━━━━━━━━━━━━━━\n📧 Tài khoản: <code>clone30_pro_1@gmail.com</code>\n🔑 Mật khẩu: <code>pass30vn123</code>",
    "💎 <b>ACC CLONE LEVEL 30</b>\n━━━━━━━━━━━━━━━━━━━\n📧 Tài khoản: <code>clone30_vip_99@gmail.com</code>\n🔑 Mật khẩu: <code>ffpro2026</code>"
]

FAKE_ACCOUNTS_CLONE58 = [
    "🔥 <b>ACC CLONE LEVEL 5</b>\n━━━━━━━━━━━━━━━━━━━\n📧 Tài khoản: <code>clone58_1@gmail.com</code>\n🔑 Mật khẩu: <code>clone123456</code>",
    "🔥 <b>ACC CLONE LEVEL 5</b>\n━━━━━━━━━━━━━━━━━━━\n📧 Tài khoản: <code>clone58_2@gmail.com</code>\n🔑 Mật khẩu: <code>abcxyz789</code>"
]

flask_app = Flask(__name__)
application = Application.builder().token(TOKEN).updater(None).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    get_user(user_id)

    args = context.args
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].split("_")[1])
            if referrer_id != user_id:
                u_data = get_user(user_id)
                if not u_data["has_been_referred"]:
                    update_user_field(user_id, "has_been_referred", 1)
                    update_user_field(user_id, "referrer_id", referrer_id)
        except Exception as e:
            logger.error(f"Lỗi ref: {e}")

    u_data = get_user(user_id)
    if u_data["joined"] == 1:
        await send_main_menu(update, context)
        return

    is_joined = False
    try:
        member = await context.bot.get_chat_member(chat_id=GROUP_CHAT_ID, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            is_joined = True
    except Exception as e:
        logger.error(f"Lỗi check join: {e}")

    if is_joined:
        update_user_field(user_id, "joined", 1)
        u_data = get_user(user_id)
        if u_data["has_been_referred"] == 1 and u_data["reward_given"] == 0:
            referrer_id = u_data["referrer_id"]
            add_user_xu(referrer_id, 2)
            update_user_field(user_id, "reward_given", 1)
            try:
                await context.bot.send_message(chat_id=referrer_id, text="🎉 <b>Có người vừa join kênh qua link của bạn! (+2 xu).</b>", parse_mode="HTML")
            except Exception:
                pass
        await send_main_menu(update, context)
        return

    keyboard = [
        [InlineKeyboardButton("📢 Tham gia Kênh", url="https://t.me/nhomsharemodallgame")],
        [InlineKeyboardButton("✅ Tôi đã tham gia", callback_data="check_joined")]
    ]
    if update.message:
        await update.message.reply_text("<b>⚠️ Bạn cần tham gia kênh @nhomsharemodallgame trước khi sử dụng bot!</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def check_joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(chat_id=GROUP_CHAT_ID, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            update_user_field(user_id, "joined", 1)
            u_data = get_user(user_id)
            if u_data["has_been_referred"] == 1 and u_data["reward_given"] == 0:
                referrer_id = u_data["referrer_id"]
                add_user_xu(referrer_id, 2)
                update_user_field(user_id, "reward_given", 1)
                try:
                    await context.bot.send_message(chat_id=referrer_id, text="🎉 <b>Có người vừa join kênh qua link của bạn! (+2 xu).</b>", parse_mode="HTML")
                except Exception:
                    pass
            try:
                await query.message.delete()
            except Exception:
                pass
            await send_main_menu_callback(query, context)
        else:
            await query.answer("❌ Bạn chưa tham gia kênh!", show_alert=True)
    except Exception:
        await query.answer("❌ Lỗi kiểm tra!", show_alert=True)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u_data = get_user(user_id)
    ht = get_stock("huyen_thoai")
    c30 = get_stock("clone30")
    c58 = get_stock("clone58")
    
    text = (
        "🎮 <b>HỆ THỐNG ĐỔI ACC FREE FIRE VIP</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>Rank Huyền Thoại (1-5 sao):</b> <code>{ht}</code> acc <i>(Giá: 30 xu)</i>\n"
        f"💎 <b>Clone Lv 30:</b> <code>{c30}</code> acc <i>(Giá: 20 xu)</i>\n"
        f"🔥 <b>Clone Lv 5:</b> <code>{c58}</code> acc <i>(Giá: 15 xu)</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Số dư tài khoản:</b> <code>{u_data['xu']} xu</code>\n"
        "📌 <i>Cách kiếm thêm xu: Bấm vào nút 'Kiếm Xu' bên dưới để lấy link mời bạn bè (1 Ref = 2 xu).</i>"
    )
    keyboard = [
        [InlineKeyboardButton(f"🏆 Đổi Rank Huyền Thoại ({ht} còn)", callback_data="doi_huyen_thoai")],
        [InlineKeyboardButton(f"💎 Đổi Clone Lv 30 ({c30} còn)", callback_data="doi_clone30")],
        [InlineKeyboardButton(f"🔥 Đổi Clone Lv 5 ({c58} còn)", callback_data="doi_clone58")],
        [InlineKeyboardButton("🎁 Kiếm Xu (Lấy Link Ref)", callback_data="kiem_xu")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def send_main_menu_callback(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    u_data = get_user(user_id)
    ht = get_stock("huyen_thoai")
    c30 = get_stock("clone30")
    c58 = get_stock("clone58")
    
    text = (
        "🎮 <b>HỆ THỐNG ĐỔI ACC FREE FIRE VIP</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>Rank Huyền Thoại (1-5 sao):</b> <code>{ht}</code> acc <i>(Giá: 30 xu)</i>\n"
        f"💎 <b>Clone Lv 30:</b> <code>{c30}</code> acc <i>(Giá: 20 xu)</i>\n"
        f"🔥 <b>Clone Lv 5:</b> <code>{c58}</code> acc <i>(Giá: 15 xu)</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Số dư tài khoản:</b> <code>{u_data['xu']} xu</code>\n"
        "📌 <i>Cách kiếm thêm xu: Bấm vào nút 'Kiếm Xu' bên dưới để lấy link mời bạn bè (1 Ref = 2 xu).</i>"
    )
    keyboard = [
        [InlineKeyboardButton(f"🏆 Đổi Rank Huyền Thoại ({ht} còn)", callback_data="doi_huyen_thoai")],
        [InlineKeyboardButton(f"💎 Đổi Clone Lv 30 ({c30} còn)", callback_data="doi_clone30")],
        [InlineKeyboardButton(f"🔥 Đổi Clone Lv 5 ({c58} còn)", callback_data="doi_clone58")],
        [InlineKeyboardButton("🎁 Kiếm Xu (Lấy Link Ref)", callback_data="kiem_xu")]
    ]
    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "check_joined":
        await check_joined_callback(update, context)
        return

    u_data = get_user(user_id)

    if data == "doi_huyen_thoai":
        ht = get_stock("huyen_thoai")
        if ht <= 0:
            await query.answer("❌ Kho Acc Huyền Thoại đã hết hàng!", show_alert=True)
        elif u_data["xu"] < 30:
            await query.answer("❌ Bạn không đủ 30 xu để đổi!", show_alert=True)
        else:
            add_user_xu(user_id, -30)
            update_stock("huyen_thoai", -1)
            acc_info = random.choice(FAKE_ACCOUNTS_HUYEN_THOAI)
            await query.answer("🎉 Đổi thành công!", show_alert=False)
            await context.bot.send_message(chat_id=user_id, text=f"✅ <b>GIAO DỊCH THÀNH CÔNG</b>\n\n{acc_info}", parse_mode="HTML")

    elif data == "doi_clone30":
        c30 = get_stock("clone30")
        if c30 <= 0:
            await query.answer("❌ Kho Acc Clone Lv 30 đã hết hàng!", show_alert=True)
        elif u_data["xu"] < 20:
            await query.answer("❌ Bạn không đủ 20 xu để đổi!", show_alert=True)
        else:
            add_user_xu(user_id, -20)
            update_stock("clone30", -1)
            acc_info = random.choice(FAKE_ACCOUNTS_CLONE30)
            await query.answer("🎉 Đổi thành công!", show_alert=False)
            await context.bot.send_message(chat_id=user_id, text=f"✅ <b>GIAO DỊCH THÀNH CÔNG</b>\n\n{acc_info}", parse_mode="HTML")
            
    elif data == "doi_clone58":
        c58 = get_stock("clone58")
        if c58 <= 0:
            await query.answer("❌ Kho Acc Clone Lv 5 đã hết hàng!", show_alert=True)
        elif u_data["xu"] < 15:
            await query.answer("❌ Bạn không đủ 15 xu để đổi!", show_alert=True)
        else:
            add_user_xu(user_id, -15)
            update_stock("clone58", -1)
            acc_info = random.choice(FAKE_ACCOUNTS_CLONE58)
            await query.answer("🎉 Đổi thành công!", show_alert=False)
            await context.bot.send_message(chat_id=user_id, text=f"✅ <b>GIAO DỊCH THÀNH CÔNG</b>\n\n{acc_info}", parse_mode="HTML")
            
    elif data == "kiem_xu":
        ref_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        await query.answer("Đã tạo link!", show_alert=True)
        await context.bot.send_message(chat_id=user_id, text=f"🔗 <b>Link giới thiệu của bạn:</b>\n<code>{ref_link}</code>", parse_mode="HTML")

# Lệnh cộng xu (Chỉ Admin mới dùng được)
async def admin_addxu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bạn không có quyền dùng lệnh này.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Dùng cú pháp: /addxu [ID] [Số xu]")
        return

    try:
        target_id = int(args[0])
        amount = int(args[1])
        add_user_xu(target_id, amount)
        await update.message.reply_text("✅ Đã thêm xu hoàn tất!")
        try:
            await context.bot.send_message(chat_id=target_id, text=f"🎁 Bạn được cộng <b>{amount} xu</b> từ Admin!", parse_mode="HTML")
        except Exception:
            pass
    except ValueError:
        await update.message.reply_text("❌ ID và số xu phải là số!")

# Lệnh chỉnh kho (Chỉ Admin mới dùng được)
async def admin_setstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bạn không có quyền dùng lệnh này.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Dùng cú pháp: /setstock [huyen_thoai/clone30/clone58] [Số lượng]")
        return

    item_type = args[0]
    try:
        quantity = int(args[1])
        if item_type not in ["huyen_thoai", "clone30", "clone58"]:
            await update.message.reply_text("❌ Loại kho không hợp lệ! Dùng: huyen_thoai, clone30, hoặc clone58")
            return
            
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO stock (item_type, quantity) VALUES (?, ?)", (item_type, quantity))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Đã cập nhật kho <b>{item_type}</b> thành <b>{quantity}</b> acc!", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ Số lượng phải là số nguyên!")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("addxu", admin_addxu))
application.add_handler(CommandHandler("setstock", admin_setstock))
application.add_handler(CallbackQueryHandler(button_handler))

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, application.bot)
    async def run_update():
        if not application.running:
            await application.initialize()
        await application.process_update(update)
    asyncio.run(run_update())
    return "OK", 200

@flask_app.route("/", methods=["GET"])
def index():
    return "Bot running 24/7!", 200

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=PORT)
