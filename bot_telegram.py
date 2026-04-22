import logging
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

# ─── CONFIGURAÇÕES ───────────────────────────────────────────
TOKEN = "8210254016:AAHf3UTJziJqFJ_jP3_uOyI7Z6CT0zS-KFI"
ADMIN_ID = 7281731886     # ID do Telegram da sua cliente
CHAVE_PIX = "c78c03f8-00de-400e-9d67-5b7cd10651fc"

PLANOS = {
    "semanal": {"nome": "Semanal", "preco": "R$ 39,99", "emoji": "📅"},
    "mensal":  {"nome": "Mensal",  "preco": "R$ 69,99", "emoji": "📆"},
    "trimestral": {"nome": "Trimestral 🔥 PROMOÇÃO", "preco": "R$ 189,90", "emoji": "💎"},
}

# ─── ESTADOS DO FLUXO ────────────────────────────────────────
NOME, PLANO, COMPROVANTE = range(3)

logging.basicConfig(level=logging.INFO)

# ─── /start ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Seja bem-vindo(a)! 💕\n\n"
        "Antes de tudo, qual é o seu nome?"
    )
    return NOME

# ─── RECEBE O NOME ───────────────────────────────────────────
async def receber_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.message.text.strip()
    context.user_data["nome"] = nome

    keyboard = [
        [InlineKeyboardButton("📅 Semanal — R$ 39,99", callback_data="semanal")],
        [InlineKeyboardButton("📆 Mensal — R$ 69,99", callback_data="mensal")],
        [InlineKeyboardButton("💎 Trimestral 🔥 PROMOÇÃO — R$ 189,90", callback_data="trimestral")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Prazer, {nome}! 😊\n\n"
        "Confira nossos planos exclusivos e escolha o melhor pra você:",
        reply_markup=reply_markup,
    )
    return PLANO

# ─── RECEBE O PLANO ──────────────────────────────────────────
async def receber_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plano_key = query.data
    plano = PLANOS[plano_key]
    context.user_data["plano"] = plano

    descricao_trimestral = (
        "\n\n🔥 *PROMOÇÃO!* Pagando de uma vez você economiza mais de R$ 20 comparado a pagar o mensal 3x!"
        if plano_key == "trimestral" else ""
    )

    await query.message.reply_text(
        f"Ótima escolha! ✨\n\n"
        f"*Plano {plano['nome']}* — *{plano['preco']}*{descricao_trimestral}\n\n"
        f"Faça o pagamento via Pix:\n\n"
        f"🔑 *Chave Pix:*\n`{CHAVE_PIX}`\n\n"
        f"Após pagar, envie o *comprovante aqui* que vou liberar seu acesso! 💕",
        parse_mode="Markdown",
    )
    return COMPROVANTE

# ─── RECEBE O COMPROVANTE ────────────────────────────────────
async def receber_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = context.user_data.get("nome", "Cliente")
    plano = context.user_data.get("plano", {})
    user = update.message.from_user

    # Avisa a admin
    mensagem_admin = (
        f"🔔 *Novo pagamento recebido!*\n\n"
        f"👤 Nome: {nome}\n"
        f"📱 Username: @{user.username or 'sem username'}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Plano: {plano.get('nome', '?')} — {plano.get('preco', '?')}\n\n"
        f"Verifique o comprovante e envie o link do grupo para o cliente!"
    )

    try:
        # Encaminha o comprovante pra admin
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=mensagem_admin,
                parse_mode="Markdown",
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=update.message.document.file_id,
                caption=mensagem_admin,
                parse_mode="Markdown",
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=mensagem_admin + f"\n\n📄 Mensagem do cliente: {update.message.text}",
                parse_mode="Markdown",
            )
    except Exception as e:
        logging.error(f"Erro ao notificar admin: {e}")

    # Responde ao cliente
    await update.message.reply_text(
        "✅ Comprovante recebido!\n\n"
        "Estou verificando seu pagamento e em instantes você receberá o link de acesso. 💕\n\n"
        "Aguarde um momentinho! 🙏"
    )
    return ConversationHandler.END

# ─── CANCELAR ────────────────────────────────────────────────
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Atendimento encerrado. Digite /start para recomeçar! 😊")
    return ConversationHandler.END

# ─── MAIN ────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome)],
            PLANO: [CallbackQueryHandler(receber_plano)],
            COMPROVANTE: [
                MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT & ~filters.COMMAND, receber_comprovante)
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv)
    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
