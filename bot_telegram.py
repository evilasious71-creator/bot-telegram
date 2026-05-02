import logging
import os
import threading
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
CANAL_PUBLICO = "https://t.me/euzinhaoficiall"
GRUPO_ID = None
PORT = int(os.environ.get("PORT", 8080))

PLANOS = {
    "semanal": {"nome": "Semanal", "preco": "R$ 39,99"},
    "mensal":  {"nome": "Mensal",  "preco": "R$ 69,99"},
    "trimestral": {"nome": "Trimestral 🔥 PROMOÇÃO", "preco": "R$ 189,90"},
}

clientes_pendentes = {}

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
        f"Olá! Seja bem-vindo(a)! 💕\n\n"
        f"Antes de me seguir, confira nosso canal:\n{CANAL_PUBLICO}\n\n"
        f"Qual é o seu nome?"
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

    keyboard_pix = [
        [InlineKeyboardButton("📋 Copiar Chave Pix", copy_text=CHAVE_PIX)],
    ]

    await query.message.reply_text(
        f"Ótima escolha! ✨\n\n*Plano {plano['nome']}* — *{plano['preco']}*{extra}\n\n"
        f"💳 *Pagamento via Pix*\n\n"
        f"Toque no botão abaixo para copiar a chave Pix e realize o pagamento:\n\n"
        f"Após pagar, envie o *comprovante aqui* que vou liberar seu acesso! 💕\n\n"
        f"📸 *Envie apenas a foto do comprovante.*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard_pix),
    )
    return COMPROVANTE

async def comprovante_invalido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ Por favor, envie apenas a *foto do comprovante* de pagamento para continuar! 📸",
        parse_mode="Markdown",
    )
    return COMPROVANTE

async def receber_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = context.user_data.get("nome", "Cliente")
    plano = context.user_data.get("plano", {})
    user = update.message.from_user

    clientes_pendentes[str(user.id)] = {
        "nome": nome,
        "chat_id": user.id,
        "plano": plano,
        "username": user.username or "sem username"
    }

    mensagem_admin = (
        f"🔔 *Novo pagamento recebido!*\n\n"
        f"👤 Nome: {nome}\n"
        f"📱 Username: @{user.username or 'sem username'}\n"
        f"🆔 ID: `{user.id}`\n"
        f"💰 Plano: {plano.get('nome', '?')} — {plano.get('preco', '?')}\n\n"
        f"Para liberar o acesso, responda:\n`/confirmar {user.id}`"
    )
    try:
        if update.message.photo:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=mensagem_admin, parse_mode="Markdown")
        elif update.message.document:
            await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=mensagem_admin, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Erro ao notificar admin: {e}")

    await update.message.reply_text(
        "✅ Comprovante recebido!\n\n"
        "Estou verificando seu pagamento e em instantes você receberá o link de acesso. 💕\n\n"
        "Aguarde um momentinho! 🙏"
    )
    return ConversationHandler.END

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Você não tem permissão para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❌ Use: /confirmar ID_DO_CLIENTE")
        return

    cliente_id = context.args[0]
    cliente = clientes_pendentes.get(cliente_id)

    if not cliente:
        await update.message.reply_text("❌ Cliente não encontrado. Verifique o ID.")
        return

    if not GRUPO_ID:
        await update.message.reply_text("❌ ID do grupo não configurado ainda!")
        return

    try:
        link = await context.bot.create_chat_invite_link(
            chat_id=GRUPO_ID,
            member_limit=1,
            name=f"Acesso - {cliente['nome']}"
        )

        await context.bot.send_message(
            chat_id=cliente["chat_id"],
            text=f"✅ Pagamento confirmado!\n\n"
                 f"Aqui está seu link exclusivo de acesso:\n{link.invite_link}\n\n"
                 f"⚠️ Este link é de uso único, não compartilhe!\n\n"
                 f"Seja bem-vindo(a)! 💕"
        )

        del clientes_pendentes[cliente_id]
        await update.message.reply_text(f"✅ Link enviado para {cliente['nome']} com sucesso!")

    except Exception as e:
        logging.error(f"Erro ao gerar link: {e}")
        await update.message.reply_text(f"❌ Erro ao gerar link: {e}")

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Atendimento encerrado. Digite /start para recomeçar! 😊")
    return ConversationHandler.END

def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome)],
            PLANO: [CallbackQueryHandler(receber_plano)],
            COMPROVANTE: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receber_comprovante),
                MessageHandler(filters.TEXT & ~filters.COMMAND, comprovante_invalido),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("confirmar", confirmar))
    print("Bot rodando!")
    app.run_polling()

if __name__ == "__main__":
    main()
