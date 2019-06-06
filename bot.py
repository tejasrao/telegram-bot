from telegram.ext import (Updater, CommandHandler,
                          MessageHandler, Filters, CallbackQueryHandler)
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
from telegram import ParseMode, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ChatAction
from functools import wraps
import logging
import json
import os
import subprocess
import random
import sys
import inspect
from threading import Thread


class Sadaharu:

    def __init__(self):
        self.files = dict()
        self.subs = dict()
        self.GROUPS = open("groups.txt").read().split('\n')
        self.ADMINS = open("admin.txt").read().split('\n')
        self.TOKEN = open("token.txt").readline().strip()

    def getMetadata(self):
        with open("files/metadata.json") as file:
            return json.loads(file.read())

    def updateFiles(self):
        metadata = self.getMetadata()
        self.files = dict()
        for file_id, vals in metadata["files"].items():
            self.files.update({
                file_id: vals["file_name"]
            })
        subjects = [i for i in metadata["subjects"].keys()]
        for i in subjects:
            val = i.split('-')
            if val[0] in self.subs:
                self.subs[val[0]].append(val[1])
            else:
                self.subs[val[0]] = [val[1]]

    def updateMetadata(self, data):
        with open("files/metadata.json", "w") as file:
            json.dump(data, file, sort_keys=True, indent=2)
        self.updateFiles()

    def send_action(action):
        """Sends `action` while processing func command."""
        def decorator(func):
            @wraps(func)
            def command_func(*args, **kwargs):
                bot, update = args
                bot.send_chat_action(
                    chat_id=update.effective_message.chat_id, action=action)
                return func(bot, update, **kwargs)
            return command_func

        return decorator

    def restricted(func):
        @wraps(func)
        def wrapped(bot, update, *args, **kwargs):
            LIST_OF_ADMINS = self.ADMINS + self.GROUPS
            try:
                user_id = update.message.chat.id
                chat = update.message.chat
                reply = update.message.reply_text
            except:
                user_id = update.callback_query.message.chat_id
                chat = update.callback_query.message.chat
                reply = update.callback_query.message.reply_text
            if user_id not in LIST_OF_ADMINS:
                print("Unauthorized access denied for {}.".format(chat))
                sticker = ['CAADBQADLwADwZuBCAeTKdJv0cY8Ag', 'CAADBQADIQIAAj3XUhMm-CrDG00mvgI', 'CAADBQADpQADwZuBCLa7SOf3XTyFAg', 'CAADAwADawQAArs-WAafB0v2l_OLoAI',
                           'CAADAwADdAAD_ZPKAAEzVqA9_Yp9hgI', 'CAADAwADkAAD_ZPKAAHKuP9rrq1ctAI', 'CAADBAADcgEAAqdGcwgyUwABiYLXJp4C', 'CAADBAADhxAAAteR0AHQ4WiFtJJj0AI']
                bot.sendSticker(chat.id, random.choice(sticker))
                reply(
                    "You are unauthorised. Contact with admin - @tejas_rao")
                return
            return func(bot, update, *args, **kwargs)
        return wrapped

    @restricted
    @send_action(ChatAction.TYPING)
    def start(self, bot, update):
        update.message.reply_text(
            "I can help you to organize files and find information related to current syllabus, timetable, events, etc.")

    @restricted
    @send_action(ChatAction.TYPING)
    def refresh(self, bot, update):
        self.updateFiles()
        bot.sendSticker(chat_id=update.message.chat_id,
                        sticker="CAADAwADeAAD_ZPKAAGQVkKUAAFaU7kC")
        bot.sendMessage(chat_id=update.message.chat_id, text="✨ Refreshing ✨")

    def build_menu(self, buttons,
                   n_cols=1,
                   header_buttons=None,
                   footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu

    @restricted
    @send_action(ChatAction.TYPING)
    def display(self, bot, update):
        global files
        if len(files.keys()) == 0:
            update.message.reply_text("Nothing to display")
            return
        button_list = [InlineKeyboardButton(
            val, callback_data=val) for val in files.values()]
        reply_markup = InlineKeyboardMarkup(
            self.build_menu(button_list))
        update.message.reply_text(
            "Select an option 👇", reply_markup=reply_markup)

    def storeCourse(self, bot, update, msg, data):
        global subs
        sub, unit = msg[0].upper(), msg[1]
        metadata = self.getMetadata()
        metadata['count'] += 1
        if sub in subs.keys() and unit in subs[sub]:
            update.message.reply_text("Course Already Exists!")
            return
        metadata["subjects"].update({
            sub+'-'+unit: data
        })
        # bot.get_file(data["file_id"]).download("files/" + sub+'-'+unit)
        self.updateMetadata(metadata)
        update.message.reply_text("Done!😺")

    def getFileData(self, update):
        data = dict()
        file_name = update.message.text.strip().split()[1:]
        if update.message.reply_to_message.document is None:
            message = update.message.reply_to_message.photo[-1]
            data["file_name"] = file_name
        else:
            message = update.message.reply_to_message.document
            data["mime_type"] = message.mime_type
            data["file_name"] = message.file_name
        file_id = message.file_id
        data.update({
            "date": str(update.message.date.now()),
            "chat_id": update.message.chat_id,
            "file_size": message.file_size
        })
        return data, file_name, file_id

    @restricted
    @send_action(ChatAction.UPLOAD_DOCUMENT)
    def store(self, bot, update):
        try:
            data, msg, file_id = self.getFileData(update)
            if len(msg) == 3 and msg[0].upper() == 'COURSE':
                data.update({
                    "file_id": file_id
                })
                self.storeCourse(bot, update, msg[1:], data)
                return
            elif msg[0].upper() != 'COURSE':
                metadata = self.getMetadata()
                metadata['count'] += 1
                if file_id in metadata["files"].keys():
                    update.message.reply_text("File Already Exists!")
                    return
                metadata["files"].update({
                    file_id: data
                })
                # bot.get_file(data["file_id"]).download("files/" + file_name)
                self.updateMetadata(metadata)
                update.message.reply_text("Done!😺")
            else:
                raise AttributeError
        except AttributeError:
            bot.sendMessage(chat_id=update.message.chat_id,
                            text="\nUsage:\n /store[with reply to a message] \n☝ to save a normal file\n/store course <course_name> <unit_number>[with reply to a message]\n ☝ to save a subject file\n")

    @restricted
    @send_action(ChatAction.TYPING)
    def callback_handler(self, bot, update):
        try:
            metadata = self.getMetadata()
            chat_id = update.callback_query.message.chat_id
            for file_id, vals in metadata["files"].items():
                if vals["file_name"] == update.callback_query.data:
                    try:
                        reply_message = bot.sendDocument(chat_id, file_id)
                    except:
                        reply_message = bot.sendPhoto(chat_id, file_id)
                    reply_message.reply_text(
                        "@"+update.callback_query.from_user.username)
                    return
            raise Exception
        except:
            bot.sendMessage(chat_id=chat_id, text="Not Found😟")

    @restricted
    @send_action(ChatAction.TYPING)
    def rename(self, bot, update):
        global files
        try:
            new_file_name = ' '.join(
                update.message.text.strip().split(' ')[1:]).strip()
            metadata = self.getMetadata()
            try:
                try:
                    file_id = update.message.reply_to_message.document.file_id
                except:
                    file_id = update.message.reply_to_message.photo[-1].file_id
                if file_id in files.keys():
                    data = metadata["files"].pop(file_id)
                    data.update({
                        "file_name": new_file_name
                    })
                else:
                    raise KeyError
                metadata["files"].update({
                    file_id: data
                })
                update.message.reply_text("Renamed successfully!")
                self.updateMetadata(metadata)
            except KeyError:
                update.message.reply_text(
                    "File doesn't exist!! You have to save it first. 💾")
        except:
            update.message.reply_text("Usage: /rename <new_file_name>")

    @restricted
    @send_action(ChatAction.TYPING)
    def courses(self, bot, update):
        global subs
        try:
            head = "subject name - available units\n"
            msg = '\n'.join([str(idx+1)+'. '+val+' - '+', '.join(subs[val])
                             for idx, val in enumerate(subs)])
            if len(msg) == 0:
                msg = "No subjects avaliable\n"
                head = ''
            usage = "\n\nUSAGE: /course <course_name> <unit_number>\nEg. /course ds 1"
            data = update.message.text.strip().split(' ')[1:]
            if 1 <= len(data) <= 2:
                subject = data[0].upper()
                try:
                    unit = data[1]
                except IndexError:
                    unit = None
                if subject not in subs:
                    update.message.reply_text("This subject is not available!")
                    return
                elif unit != None and unit not in subs[subject]:
                    update.message.reply_text("This unit is not available!")
                    return
                file_ids = []
                metadata = self.getMetadata()
                if unit is None:
                    for i in subs[subject]:
                        file_ids.append(
                            metadata["subjects"][subject+'-'+i]["file_id"])
                else:
                    file_ids.append(
                        metadata["subjects"][subject+'-'+unit]["file_id"])
                for f_id in file_ids:
                    bot.sendDocument(
                        chat_id=update.message.chat_id, document=f_id)
            else:
                bot.sendMessage(chat_id=update.message.chat_id,
                                text=head+msg+usage)
        except TypeError:
            bot.sendMessage(chat_id=update.message.chat_id,
                            text=head+msg+usage)

    @restricted
    @send_action(ChatAction.TYPING)
    def reset(self, bot, update):
        bot.setChatPhoto(self.GROUPS, open("files/timeTable.jpg", "rb"))

    @restricted
    @send_action(ChatAction.TYPING)
    def unknown(self, bot, update):
        update.message.reply_text("Sorry, I didn't understand that command.🤔")

    def exec(self):
        updater = Updater(
            token=self.TOKEN)
        dispatcher = updater.dispatcher
        
        self.updateFiles()

        # restart_handler = CommandHandler('restart', restart, filters=Filters.user(username="@tejas_rao"))
        start_handler = CommandHandler('start', self.start)
        display_handler = CommandHandler('display', self.display)
        store_handler = CommandHandler('store', self.store)
        refresh_handler = CommandHandler(
            'refresh', self.refresh, filters=Filters.user(username="@tejas_rao"))
        rename_handler = CommandHandler('rename', self.rename)
        courses_handler = CommandHandler('courses', self.courses)
        reset_handler = CommandHandler('reset', self.reset)
        unknown_handler = MessageHandler(Filters.command, self.unknown)

        # dispatcher.add_handler(restart_handler)
        dispatcher.add_handler(start_handler)
        dispatcher.add_handler(display_handler)
        dispatcher.add_handler(store_handler)
        dispatcher.add_handler(refresh_handler)
        dispatcher.add_handler(rename_handler)
        dispatcher.add_handler(courses_handler)
        dispatcher.add_handler(CallbackQueryHandler(self.callback_handler))
        dispatcher.add_handler(unknown_handler)
        # dispatcher.add_error_handler(error_callback)

        print("Polling...")
        updater.start_polling()
        updater.idle()

def main():
    pet = Sadaharu()
    pet.exec()

if __name__ == "__main__":
    main()