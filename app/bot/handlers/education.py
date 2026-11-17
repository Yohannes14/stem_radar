"""Interactive STEM Learning Assistant handlers (Roadmaps, Lessons, Quizzes, Comparisons, Projects)."""

import logging
from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.keyboards.inline import (
    get_education_topics_keyboard,
    get_lesson_keyboard,
    get_project_card_keyboard,
    get_quiz_keyboard,
)
from app.bot.ui.formatters import (
    chunk_message,
    format_concept_comparison,
    format_interactive_lesson,
    format_learning_progress,
    format_learning_roadmap,
    format_project_recommendation,
    format_quiz_question,
    format_vocabulary_glossary,
    sanitize_markdown,
)
from app.database.database import get_session_factory
from app.database.repository import Repository
from app.services.ai import ai_service

logger = logging.getLogger(__name__)


# ------------------ Command 1: /learn ------------------


@authorized_only
async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deliver an interactive STEM lesson adapted to beginner, intermediate, or advanced level."""
    if not context.args:
        text = (
            "🎓 *STEM RADAR Learning Academy*\n\n"
            "Choose a core domain below to start learning, or type `/learn <topic>`.\n\n"
            "Examples:\n"
            "• `/learn Artificial Intelligence`\n"
            "• `/learn advanced Humanoid Kinematics`\n"
            "• `/learn beginner Quantum Computing`"
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_education_topics_keyboard()
            )
        return

    raw_args: List[str] = list(context.args)
    level = "intermediate"
    if raw_args[0].lower() in ("beginner", "intermediate", "advanced"):
        level = raw_args.pop(0).lower()

    topic = " ".join(raw_args).strip()
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"🧠 *Preparing {level}-level lesson for '{topic}'...*",
            parse_mode=ParseMode.MARKDOWN,
        )

    lesson = await ai_service.generate_lesson(topic, level=level)
    formatted = format_interactive_lesson(lesson)

    # Track progress in database
    user = update.effective_user
    if user:
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            await repo.record_lesson_completion(user.id, topic, level=level)

    chunks = chunk_message(formatted, max_length=4000)
    reply_markup = get_lesson_keyboard(topic, level)

    if status_msg:
        await status_msg.edit_text(chunks[0], parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        for extra in chunks[1:]:
            await update.effective_message.reply_text(extra, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(chunks[0], parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        for extra in chunks[1:]:
            await update.effective_message.reply_text(extra, parse_mode=ParseMode.MARKDOWN)


# ------------------ Command 2: /roadmap ------------------


@authorized_only
async def roadmap_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a 4-phase end-to-end curriculum roadmap for any STEM topic."""
    if not context.args:
        text = (
            "🗺️ *STEM Learning Roadmaps*\n\n"
            "Select a featured topic or type `/roadmap <topic>` to generate a 4-phase master curriculum.\n\n"
            "Examples:\n"
            "• `/roadmap Robotics`\n"
            "• `/roadmap Deep Learning`\n"
            "• `/roadmap Embedded Systems`"
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_education_topics_keyboard()
            )
        return

    topic = " ".join(context.args).strip()
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"🗺️ *Synthesizing 4-phase engineering roadmap for '{topic}'...*",
            parse_mode=ParseMode.MARKDOWN,
        )

    roadmap = await ai_service.generate_roadmap(topic)
    formatted = format_learning_roadmap(roadmap)
    chunks = chunk_message(formatted, max_length=4000)

    if status_msg:
        await status_msg.edit_text(chunks[0], parse_mode=ParseMode.MARKDOWN)
        for extra in chunks[1:]:
            await update.effective_message.reply_text(extra, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        for chunk in chunks:
            await update.effective_message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


# ------------------ Command 3: /quiz ------------------


@authorized_only
async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Launch an interactive multiple-choice STEM quiz."""
    raw_args: List[str] = list(context.args) if context.args else []
    level = "intermediate"
    if raw_args and raw_args[0].lower() in ("beginner", "intermediate", "advanced"):
        level = raw_args.pop(0).lower()

    topic = " ".join(raw_args).strip() if raw_args else "Computer Science"
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"📝 *Generating interactive technical quiz for '{topic}' ({level})...*",
            parse_mode=ParseMode.MARKDOWN,
        )

    quiz = await ai_service.generate_quiz(topic, difficulty=level)
    formatted = format_quiz_question(quiz, question_index=0)
    reply_markup = get_quiz_keyboard(topic, q_index=0, total_q=len(quiz.questions))

    if status_msg:
        await status_msg.edit_text(formatted, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# ------------------ Command 4: /compare ------------------


@authorized_only
async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Compare two technical concepts or architectures side-by-side."""
    if not context.args:
        text = (
            "⚖️ *Technical Concept Comparison*\n\n"
            "Compare two frameworks, architectures, or concepts side-by-side.\n\n"
            "Usage: `/compare <concept A> vs <concept B>`\n\n"
            "Examples:\n"
            "• `/compare PyTorch vs JAX`\n"
            "• `/compare REST vs gRPC`\n"
            "• `/compare Monolith vs Microservices`\n"
            "• `/compare Transformer vs Mamba State Space`"
        )
        if update.effective_message:
            await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    raw_query = " ".join(context.args)
    if " vs " in raw_query:
        parts = raw_query.split(" vs ", 1)
    elif " and " in raw_query:
        parts = raw_query.split(" and ", 1)
    elif "," in raw_query:
        parts = raw_query.split(",", 1)
    else:
        parts = [context.args[0], " ".join(context.args[1:]) if len(context.args) > 1 else "Alternative"]

    concept_a, concept_b = parts[0].strip(), parts[1].strip()

    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"⚖️ *Comparing '{concept_a}' vs '{concept_b}'...*",
            parse_mode=ParseMode.MARKDOWN,
        )

    comp = await ai_service.compare_concepts(concept_a, concept_b)
    formatted = format_concept_comparison(comp)
    chunks = chunk_message(formatted, max_length=4000)

    if status_msg:
        await status_msg.edit_text(chunks[0], parse_mode=ParseMode.MARKDOWN)
        for extra in chunks[1:]:
            await update.effective_message.reply_text(extra, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        for chunk in chunks:
            await update.effective_message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


# ------------------ Command 5: /project ------------------


@authorized_only
async def project_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recommend a practical, portfolio-building engineering project."""
    raw_args: List[str] = list(context.args) if context.args else []
    level = "intermediate"
    if raw_args and raw_args[0].lower() in ("beginner", "intermediate", "advanced"):
        level = raw_args.pop(0).lower()

    topic = " ".join(raw_args).strip() if raw_args else "Robotics"
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"🚀 *Designing portfolio project for '{topic}' ({level})...*",
            parse_mode=ParseMode.MARKDOWN,
        )

    proj = await ai_service.recommend_project(topic, difficulty=level)
    formatted = format_project_recommendation(proj)
    chunks = chunk_message(formatted, max_length=4000)
    reply_markup = get_project_card_keyboard(topic, difficulty=level)

    if status_msg:
        await status_msg.edit_text(chunks[0], parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        for extra in chunks[1:]:
            await update.effective_message.reply_text(extra, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(chunks[0], parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        for extra in chunks[1:]:
            await update.effective_message.reply_text(extra, parse_mode=ParseMode.MARKDOWN)


# ------------------ Command 6: /vocabulary ------------------


@authorized_only
async def vocabulary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a curated glossary of essential technical terms for a STEM domain."""
    topic = " ".join(context.args).strip() if context.args else "Artificial Intelligence"
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"📚 *Curating technical vocabulary glossary for '{topic}'...*",
            parse_mode=ParseMode.MARKDOWN,
        )

    glossary = await ai_service.generate_vocabulary(topic)
    formatted = format_vocabulary_glossary(glossary)
    chunks = chunk_message(formatted, max_length=4000)

    if status_msg:
        await status_msg.edit_text(chunks[0], parse_mode=ParseMode.MARKDOWN)
        for extra in chunks[1:]:
            await update.effective_message.reply_text(extra, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        for chunk in chunks:
            await update.effective_message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


# ------------------ Command 7: /progress ------------------


@authorized_only
async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display user's learning progress and quiz score mastery."""
    user = update.effective_user
    user_id = user.id if user else 0

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        history = await repo.get_user_learning_history(user_id)

    formatted = format_learning_progress(history)
    if update.effective_message:
        await update.effective_message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN)


# ------------------ Education Callback Router ------------------


@authorized_only
async def education_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle interactive education button callbacks (quiz answers, levels, lessons)."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    user = update.effective_user
    user_id = user.id if user else 0

    # 1. Answer Quiz Question: qz_ans:<topic>:<q_idx>:<choice_idx>
    if data.startswith("qz_ans:"):
        await query.answer()
        parts = data.split(":")
        topic = parts[1]
        q_idx = int(parts[2])
        chosen_opt = int(parts[3])

        quiz = await ai_service.generate_quiz(topic)
        total_q = len(quiz.questions)
        q = quiz.questions[min(q_idx, total_q - 1)]

        is_correct = chosen_opt == q.correct_option_index
        icon = "✅ Correct!" if is_correct else "❌ Incorrect"
        correct_letter = chr(ord("A") + q.correct_option_index)

        feedback_lines = [
            f"{icon}\n",
            f"*Your choice:* Option {chr(ord('A') + chosen_opt)}",
            f"*Correct answer:* Option {correct_letter}\n",
            f"💡 *Explanation:*\n_{sanitize_markdown(q.explanation)}_",
        ]

        # Record score in database
        score_val = 1 if is_correct else 0
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            await repo.record_quiz_completion(user_id, topic, score=score_val, max_score=1)

        # Next question button if available
        buttons = []
        if q_idx + 1 < total_q:
            buttons.append([InlineKeyboardButton("➡️ Next Question", callback_data=f"qz_next:{topic}:{q_idx + 1}")])
        else:
            buttons.append([InlineKeyboardButton("📊 View Learning Progress", callback_data="ed_prog")])

        if query.message:
            await query.message.reply_text(
                "\n".join(feedback_lines),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
            )
        return

    # 2. Next Quiz Question: qz_next:<topic>:<q_idx>
    if data.startswith("qz_next:"):
        await query.answer()
        parts = data.split(":")
        topic = parts[1]
        q_idx = int(parts[2])

        quiz = await ai_service.generate_quiz(topic)
        formatted = format_quiz_question(quiz, question_index=q_idx)
        reply_markup = get_quiz_keyboard(topic, q_index=q_idx, total_q=len(quiz.questions))

        if query.message:
            await query.message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        return

    # 3. Trigger Quiz for Topic: ed_quiz:<topic>
    if data.startswith("ed_quiz:"):
        await query.answer("Generating quiz...")
        topic = data.split(":", 1)[1]
        quiz = await ai_service.generate_quiz(topic)
        formatted = format_quiz_question(quiz, question_index=0)
        reply_markup = get_quiz_keyboard(topic, q_index=0, total_q=len(quiz.questions))
        if query.message:
            await query.message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        return

    # 4. Trigger Roadmap: ed_map:<topic>
    if data.startswith("ed_map:"):
        await query.answer("Generating roadmap...")
        topic = data.split(":", 1)[1]
        roadmap = await ai_service.generate_roadmap(topic)
        formatted = format_learning_roadmap(roadmap)
        if query.message:
            await query.message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN)
        return

    # 5. Trigger Project: ed_prj:<topic>
    if data.startswith("ed_prj:"):
        await query.answer("Designing project...")
        topic = data.split(":", 1)[1]
        proj = await ai_service.recommend_project(topic, difficulty="intermediate")
        formatted = format_project_recommendation(proj)
        reply_markup = get_project_card_keyboard(topic, difficulty="intermediate")
        if query.message:
            await query.message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        return

    # 6. Switch Level: ed_lvl:<topic>:<level>
    if data.startswith("ed_lvl:"):
        await query.answer("Switching level...")
        parts = data.split(":")
        topic, level = parts[1], parts[2]
        lesson = await ai_service.generate_lesson(topic, level=level)
        formatted = format_interactive_lesson(lesson)
        reply_markup = get_lesson_keyboard(topic, level)
        if query.message:
            await query.message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        return

    # 7. Start Learning from topic button: ed_learn:<topic>
    if data.startswith("ed_learn:"):
        await query.answer("Loading lesson...")
        topic = data.split(":", 1)[1]
        lesson = await ai_service.generate_lesson(topic, level="beginner")
        formatted = format_interactive_lesson(lesson)
        reply_markup = get_lesson_keyboard(topic, "beginner")
        if query.message:
            await query.message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        return

    # 8. View Progress: ed_prog
    if data == "ed_prog":
        await query.answer()
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            history = await repo.get_user_learning_history(user_id)
        formatted = format_learning_progress(history)
        if query.message:
            await query.message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN)
        return
