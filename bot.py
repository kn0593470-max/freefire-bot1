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
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "@genplaycluod")
PORT = int(os.getenv("PORT", "8080"))
ADMIN_ID = 7907990385  # ID Admin của ông

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
        [InlineKeyboardButton("📢 Tham gia Kênh", url="https://t.me/genplaycluod")],
        [InlineKeyboardButton("✅ Tôi đã tham gia", callback_data="check_joined")]
    ]
    if update.message:
        await update.message.reply_text("<b>⚠️ Bạn cần tham gia kênh @genplaycluod trước khi sử dụng bot!</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

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

# --- CÁC LỆNH DÀNH RIÊNG CHO ADMIN ---
async def admin_congxu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Cú pháp: /congxu <user_id> <số_xu>\n(Dùng số âm để trừ xu, ví dụ: /congxu 12345 50)")
        return
    try:
        target_id = int(args[0])
        amount = int(args[1])
        add_user_xu(target_id, amount)
        await update.message.reply_text(f"✅ Đã cộng {amount} xu cho user <code>{target_id}</code> thành công!", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

async def admin_congkho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Cú pháp: /congkho <huyen_thoai / clone30 / clone58> <số_lượng>")
        return
    item_type = args[0]
    if item_type not in ["huyen_thoai", "clone30", "clone58"]:
        await update.message.reply_text("❌ Loại vật phẩm không hợp lệ! Chọn: huyen_thoai, clone30, clone58")
        return
    try:
        amount = int(args[1])
        new_qty = update_stock(item_type, amount)
        await update.message.reply_text(f"✅ Đã cập nhật kho <b>{item_type}</b>. Số lượng hiện tại: <code>{new_qty}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

async def admin_thongke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(xu) FROM users")
    row = cursor.fetchone()
    total_users = row[0] if row[0] else 0
    total_xu = row[1] if row[1] else 0
    conn.close()

    ht = get_stock("huyen_thoai")
    c30 = get_stock("clone30")
    c58 = get_stock("clone58")

    text = (
        "📊 <b>THỐNG KÊ HỆ THỐNG BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Tổng số user: <code>{total_users}</code>\n"
        f"💰 Tổng xu lưu hành: <code>{total_xu} xu</code>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 Kho Huyền Thoại: <code>{ht}</code> acc\n"
        f"💎 Kho Clone Lv 30: <code>{c30}</code> acc\n"
        f"🔥 Kho Clone Lv 5: <code>{c58}</code> acc"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    message_text = " ".join(context.args)
    if not message_text:
        await update.message.reply_text("⚠️ Cú pháp: /broadcast <Nội dung thông báo>")
        return

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success = 0
    failed = 0
    status_msg = await update.message.reply_text("🚀 Đang gửi broadcast...")

    for (uid,) in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 <b>THÔNG BÁO TỪ ADMIN:</b>\n\n{message_text}", parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05) # Tránh bị Telegram giới hạn spam rate
        except Exception:
            failed += 1

    await status_msg.edit_text(f"✅ <b>Gửi broadcast hoàn tất!</b>\n- Thành công: {success}\n- Thất bại: {failed}", parse_mode="HTML")
