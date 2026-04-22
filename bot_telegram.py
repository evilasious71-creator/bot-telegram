import logging
import os
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

TOKEN = "8210254016:AAHf3UTJziJqFJ_jP3_uOyI7Z6CT0zS-KFI"
ADMIN_ID = 7281731886
CHAVE_PIX = "c78c03f8-00de-400e-9d67-5b7cd10651fc"
PORT = int(os.environ.get("PORT", 8080))

PLANOS = {
    "semanal": {"nome": "Semanal", "preco": "R$ 39,99"},
    "mensal":  {"nome": "Mensal",  "preco": "R$ 69,99"},
    "trimestral": {"nome": "Trimestral 🔥 PROMOÇÃO", "preco": "R$ 189,90"},
}

NOME, PLANO, COMPROVANTE = range(3)
logging.basicConfig(level=logging.INFO)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot rodando!")
    def log_message(self, format, *args):
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Seja bem-vindo(a)! 💕\n\nAntes de tudo, qual é o seu nome?"
    )
    return NOME

async def receber_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.message.text.strip()
    context.user_data["nome"] = nome
    keyboard = [
        [InlineKeyboardButton("📅 Semanal — R$ 39,99", callback_data="semanal")],
        [InlineKeyboardButton("📆 Mensal — R$ 69,99", callback_data="mensal")],
        [InlineKeyboardButton("💎 Trimestral 🔥 PROMOÇÃO — R$ 189,90", callback_data="trimestral")],
    ]
    await update.message.reply_text(
        f"Prazer, {nome}! 😊\n\nConfira nossos planos exclusivos e escolha o melhor pra você:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PLANO

async def receber_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plano_key = query.data
    plano = PLANOS[plano_key]
    context.user_data["plano"] = plano
    extra = (
        "\n\n🔥 *PROMOÇÃO!* Pagando de uma vez você economiza mais de R$ 20 comparado a pagar o mensal 3x!"
        if plano_key == "trimestral" else ""
    )
    await query.message.reply_text(
        f"Ótima escolha! ✨\n\n*Plano {plano['nome']}* — *{plano['preco']}*{extra}\n\n"
        f"Faça o pagamento via Pix:\n\n🔑 *Chave Pix:*\n`{CHAVE_PIX}`\n\n"
        f"Após pagar, envie o *comprovante aqui* que vou liberar seu acesso! 💕",
        parse_mode="Markdown",
    )
    return COMPROVANTE

async def receber_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = context.user_data.get("nome", "Cliente")
    plano = context.user_data.get("plano", {})
    user = update.message.from_user
    mensagem_admin = (
        f"🔔 *Novo pagamento recebido!*\n\n"
        f"👤 Nome: {nome}\n"
        f"📱 Username: @{user.username or 'sem username'}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Plano: {plano.get('nome', '?')} — {plano.get('preco', '?')}\n\n"
        f"Verifique o comprovante e envie o link do grupo para o cliente!"
    )
    try:
        if update.message.photo:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=mensagem_admin, parse_mode="Markdown")
        elif update.message.document:
            await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=mensagem_admin, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=mensagem_admin + f"\n\n📄 Mensagem: {update.message.text}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Erro ao notificar admin: {e}")
    await update.message.reply_text(
        "✅ Comprovante recebido!\n\nEstou verificando seu pagamento e em instantes você receberá o link de acesso. 💕\n\nAguarde um momentinho! 🙏"
    )
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Atendimento encerrado. Digite /start para recomeçar! 😊")
    return ConversationHandler.END

async def run_bot():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome)],
            PLANO: [CallbackQueryHandler(receber_plano)],
            COMPROVANTE: [MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT & ~filters.COMMAND, receber_comprovante)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    app.add_handler(conv)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("Bot rodando!")
    while True:
        await asyncio.sleep(3600)

def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"Servidor web na porta {PORT}")
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
