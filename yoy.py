import os, json, asyncio, re, string, random, aiohttp, time
from os import system, path
from time import sleep
from random import choice, randint
from base64 import b64decode

import aiohttp
from bs4 import BeautifulSoup as S
from fake_useragent import UserAgent
from datetime import datetime

from telethon import TelegramClient, functions, errors, events, types
from telethon.tl.functions.account import CheckUsernameRequest, UpdateUsernameRequest
from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest as UpdateChannelUsername
from telethon.tl.functions.channels import DeleteChannelRequest, EditPhotoRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import InputChatUploadedPhoto

# --- تعريف الألوان ---
Z = '\033[1;31m'
X = '\033[1;33m'
F = '\033[2;32m'

class Colors:
    RED = '\033[1;31m'
    GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[1;34m'
    MAGENTA = '\033[1;35m'
    CYAN = '\033[1;36m'
    WHITE = '\033[1;37m'
    RESET = '\033[0m'

# إعدادات API
api_id = '21348817'
api_hash = '545f481d612470ada5416f4f8b267c69'
session_string = '1ApWapzMBu2zplz15JW-m9Rs-ILepFbVuj82tMxHcbFJ4F6NmmJWUZ8Qk36kmfmsj9reNZfkPgdSqsuzXoNRM4GBXjCMg8b7SE5cxO1YzL4iDQDa7XnsA1YXqqDN7dhE9vS2Surmei35Hz0KtJX0lShoZrHjnW8KgdxQ_MzE2A_CQ9eBvXtPe-numrntW2doYiMf1_dotnmdg_vy4uLS7Gq9S2HT7VXnXXojyNPEOdHUR9UEa24CbnosxvD2WIC3muxSt0reJV7xuJiB9Wyd-z_aW6mDYYglc8R9zWR26CEt80r80ROUogKkI0lICx5EuGnzY1tXYKhFsmnbPqWsmgFGvJ4ztKTk='

# معلومات المطور
developer = "@ra_a_a"
support_channel = "@ra_a_a"

class UltraUsernameClaimer:
    def __init__(self, client):
        self.client = client
        self.phone = None
        self.names = set()
        self.clicks = 0
        self.start_time = datetime.now()
        self.available_usernames = []
        self.premium_usernames = []
        self.is_running = False # يبدأ متوقفاً
        self.session = None
        self.main_task = None # لتتبع مهمة الفحص
        
        # إنشاء مجلدات التصفية
        self.filter_dir = "فلترة_اليوزرات"
        os.makedirs(self.filter_dir, exist_ok=True)
        
        # ملفات حفظ اليوزرات المعيبة
        self.banned_file = os.path.join(self.filter_dir, "فلترة_banned.txt")
        self.unknown_file = os.path.join(self.filter_dir, "فلترة_unknown.txt")
        self.invalid_file = os.path.join(self.filter_dir, "فلترة_invalid.txt")
        self.taken_file = os.path.join(self.filter_dir, "فلترة_taken.txt")
        
        
        self.filtered_usernames = set()
        self.banned_usernames = self.load_filtered_usernames(self.banned_file)
        self.unknown_usernames = self.load_filtered_usernames(self.unknown_file)
        self.invalid_usernames = self.load_filtered_usernames(self.invalid_file)
        self.taken_usernames = self.load_filtered_usernames(self.taken_file)
        
        # دمج جميع المجموعات
        self.filtered_usernames.update(self.banned_usernames)
        self.filtered_usernames.update(self.unknown_usernames)
        self.filtered_usernames.update(self.invalid_usernames)
        self.filtered_usernames.update(self.taken_usernames)
        
        print(f"{Colors.GREEN}📊 تم تحميل {len(self.filtered_usernames)} يوزر مصفى مسبقاً{Colors.RESET}")
        
        # مجموعة لتتبع اليوزرات المحفوظة
        self.saved_usernames = set()

    async def login(self):
        """تسجيل الدخول والتحقق من الاتصال"""
        try:
            if not self.client.is_connected():
                await self.client.connect()
            
            if not await self.client.is_user_authorized():
                print(f"{Colors.RED}❌ جلسة التليجرام غير صالحة أو منتهية. يرجى إنشاء جلسة جديدة.{Colors.RESET}")
                return False
            
            me = await self.client.get_me()
            print(f"{Colors.GREEN}✅ تم تسجيل الدخول بنجاح كـ: {me.first_name}{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.RED}❌ فشل تسجيل الدخول: {e}{Colors.RESET}")
            return False

    def load_filtered_usernames(self, filename):
        """تحميل اليوزرات المعيبة من ملف"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return set(line.strip().lower() for line in f if line.strip())
            return set()
        except Exception as e:
            print(f"{Colors.RED}❌ خطأ في تحميل الملف {filename}: {e}{Colors.RESET}")
            return set()

    def save_filtered_username(self, username, filename):
        """حفظ اليوزر المعيب في ملف"""
        try:
            username_lower = username.lower()
            
            if username_lower in self.saved_usernames:
                return
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(username_lower + '\n')
            
            self.filtered_usernames.add(username_lower)
            self.saved_usernames.add(username_lower)
            
        except Exception as e:
            print(f"{Colors.RED}❌ خطأ في حفظ اليوزر: {e}{Colors.RESET}")

    def setup_event_handler(self):
        """إعداد معالج الأحداث للأوامر"""
        
        @self.client.on(events.NewMessage(pattern=r'\.فحص', from_users='me'))
        async def check_handler(event):
            await self.check_status(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.الاحصائيات', from_users='me'))
        async def stats_handler(event):
            await self.detailed_stats(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.المساعدة', from_users='me'))
        async def help_handler(event):
            await self.show_help(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.اليوزرات', from_users='me'))
        async def usernames_handler(event):
            await self.show_usernames(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.ايقاف', from_users='me'))
        async def stop_handler(event):
            await self.stop_bot(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.تشغيل', from_users='me'))
        async def start_handler(event):
            await self.start_bot(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.تصفية', from_users='me'))
        async def filter_stats_handler(event):
            await self.show_filter_stats(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.المجلد', from_users='me'))
        async def folder_handler(event):
            await self.show_folder_location(event)
        
        print(f"{Colors.GREEN}✅ نظام الأوامر مفعل - اكتب (.المساعدة) في رسائلك المحفوظة لرؤية الأوامر{Colors.RESET}")

    async def check_status(self, event):
        """فحص حالة البوت"""
        current_time = datetime.now()
        uptime = current_time - self.start_time
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        status = "يعمل" if self.is_running else "متوقف"
        
        filtered_count = len(self.banned_usernames) + len(self.unknown_usernames) + len(self.invalid_usernames) + len(self.taken_usernames)
        
        status_message = (
            f"✦ ━━━━━━━ ⟡ ━━━━━━━ ✦\n"
            f"  ⚡ فحص الأداة ⚡\n"
            f"✦ ━━━━━━━ ⟡ ━━━━━━━ ✦\n\n"
            f"📊 الحالة: {status}\n"
            f"⏰ وقت البداية : {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"⏱️ مدة التشغيل : {int(hours)} ساعة و {int(minutes)} دقيقة و {int(seconds)} ثانية\n"
            f"🔢 عدد الضغطات : {self.clicks}\n"
            f"🗑️ اليوزرات المصفاة : {filtered_count}\n"
            f"✅ اليوزرات المتاحة : {len(self.available_usernames)}\n\n"
            f"✦ ━━━━━━━ ⟡ ━━━━━━━ ✦\n"
            f"⚡ {developer}"
        )
        
        await event.reply(status_message)

    async def detailed_stats(self, event):
        """إحصائيات مفصلة"""
        current_time = datetime.now()
        uptime = current_time - self.start_time
        
        hours = uptime.total_seconds() / 3600
        speed = self.clicks / hours if hours > 0 else 0
        
        filtered_count = len(self.banned_usernames) + len(self.unknown_usernames) + len(self.invalid_usernames) + len(self.taken_usernames)
        
        stats_message = (
            f"📊 الإحصائيات المفصلة\n\n"
            f"• عدد اليوزرات المفحوصة: {self.clicks}\n"
            f"• عدد اليوزرات المتاحة: {len(self.available_usernames)}\n"
            f"• عدد اليوزرات المميزة: {len(self.premium_usernames)}\n"
            f"• عدد اليوزرات المصفاة: {filtered_count}\n"
            f"• اليوزرات Taken: {len(self.taken_usernames)}\n"
            f"• سرعة الفحص: {speed:.2f} يوزر/ساعة\n"
            f"• مدة التشغيل: {str(uptime).split('.')[0]}\n"
            f"• وقت البدء: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"✦ ━━━━━━━ ⟡ ━━━━━━━ ✦"
        )
        await event.reply(stats_message)

    async def show_help(self, event):
        """عرض رسالة المساعدة"""
        help_message = (
            f"⚡ أوامر البوت ⚡\n\n"
            "`.فحص` - عرض حالة البوت الأساسية\n"
            "`.الاحصائيات` - إحصائيات مفصلة عن الأداء\n"
            "`.اليوزرات` - عرض اليوزرات المتاحة\n"
            "`.تصفية` - إحصائيات اليوزرات المصفاة\n"
            "`.المجلد` - عرض موقع مجلد التصفية\n"
            "`.ايقاف` - إيقاف البوت مؤقتاً\n"
            "`.تشغيل` - تشغيل البوت\n"
            "`.المساعدة` - عرض هذه الرسالة\n\n"
            f"📞 للمساعدة: {developer}\n\n"
            f"✦ ━━━━━━━ ⟡ ━━━━━━━ ✦"
        )
        await event.reply(help_message)

    async def show_usernames(self, event):
        """عرض اليوزرات المتاحة"""
        if not self.available_usernames:
            await event.reply("❌ لا توجد يوزرات متاحة حتى الآن")
            return
        
        usernames_list = "\n".join([f"• @{user}" for user in self.available_usernames[:10]])
        
        usernames_message = (
            f"📋 اليوزرات المتاحة\n\n"
            f"{usernames_list}\n\n"
            f"• الإجمالي: {len(self.available_usernames)} يوزر\n"
        )
        
        if self.premium_usernames:
            premium_list = "\n".join([f"• ✨ @{user}" for user in self.premium_usernames[:5]])
            usernames_message += f"\nاليوزرات المميزة:\n{premium_list}\n"
        
        usernames_message += f"\n✦ ━━━━━━━ ⟡ ━━━━━━━ ✦"
        
        await event.reply(usernames_message)

    async def stop_bot(self, event):
        """إيقاف البوت"""
        if not self.is_running:
            await event.reply("⚠️ البوت متوقف بالفعل.")
            return
        self.is_running = False
        if self.main_task:
            self.main_task.cancel() # إلغاء المهمة الحالية
        await event.reply("⏸️ تم إيقاف البوت مؤقتاً")
    
    async def start_bot(self, event):
        """تشغيل البوت"""
        if self.is_running:
            await event.reply("⚠️ البوت يعمل بالفعل.")
            return
        self.is_running = True
        await event.reply("▶️ تم تشغيل البوت")
        # بدء مهمة الفحص في الخلفية
        self.main_task = asyncio.create_task(self.generate_username_async())

    async def show_filter_stats(self, event):
        """عرض إحصائيات التصفية"""
        stats_message = (
            f"🗑️ إحصائيات اليوزرات المصفاة\n\n"
            f"• اليوزرات المبندة: {len(self.banned_usernames)}\n"
            f"• اليوزرات المجهولة: {len(self.unknown_usernames)}\n"
            f"• اليوزرات غير الصالحة: {len(self.invalid_usernames)}\n"
            f"• اليوزرات Taken: {len(self.taken_usernames)}\n\n"
            f"✦ ━━━━━━━ ⟡ ━━━━━━━ ✦"
        )
        await event.reply(stats_message)

    async def show_folder_location(self, event):
        """عرض موقع مجلد التصفية"""
        abs_path = os.path.abspath(self.filter_dir)
        
        folder_message = (
            f"📁 معلومات مجلد التصفية\n\n"
            f"• المسار: `{abs_path}`\n"
            f"• اليوزرات المبندة: {len(self.banned_usernames)}\n"
            f"• اليوزرات المجهولة: {len(self.unknown_usernames)}\n"
            f"• اليوزرات غير الصالحة: {len(self.invalid_usernames)}\n"
            f"• اليوزرات Taken: {len(self.taken_usernames)}\n\n"
            f"✦ ━━━━━━━ ⟡ ━━━━━━━ ✦"
        )
        await event.reply(folder_message)

    @staticmethod
    def usernameG():
        y = ''.join(choice('qwertyuiopasdfghjklzxcvbnm') for i in range(1))
        b = ''.join(choice('1234567890') for i in range(1))
        z = ''.join(choice('1234567890') for i in range(1))
        o = ''.join(choice('1234567890') for i in range(1))
        k = ''.join(choice('1234567890') for i in range(1))
        j = ''.join(choice('qwertyuiopasdfghjklzxcvbnm') for i in range(1))
        w = ''.join(choice('qwertyuipoasdfghjklzxcvbnm') for i in range(1))
        v = ''.join(choice('v') for i in range(1))
        i = ''.join(choice('i') for i in range(1))
        p = ''.join(choice('p') for i in range(1))
        
        v1 = y+j+y+j+y
        v2 = v+i+p+y+w
        v3 = v+i+p+w+w+w
        v4 = y+j+j+j+w
        v5 = y+j+j+j+j+j+j
        v6 = y+w+j+j+j
        v7 = y+y+y+j+j
        v8 = y+y+'_'+j+y
        v9 = y+y+'_'+j+y
        v10 = j+j+w+'_'+j
        v11 = y+ '_'+w+w+y
        v12 = w+'_'+y+w+y
        v13 = y+j+y+'_'+j
        v14 = y+y+j+j+j+j
        v15 = y+j+j+y+j
        v16 = y+'_'+w+w+y
        v17 = w+'_'+w+y+w
        v18 = y+w+y+w+w
        v38 = j+j+y+y+j+y
        v39 = j+w+w+w+y
        v40 = w+w+w+'_'+w+w+w
        v41 = w+w+'_'+w+w+w+w
        v42 = w+'_'+w+w+w+w+w
        v43 = y+w+w+w+w+w+w
        v44 = w+w+w+w+'_'+w+w
        v45 = w+w+w+w+w+'_'+w
        v46 = w+w+w+w+w+w+y
        v47 = w+'_'+w+w+w+w+w+w
        v48 = w+w+'_'+w+w+w+w+w
        v49 = w+w+w+'_'+w+w+w+w
        v50 = w+w+w+w+'_'+w+w+w
        v51 = w+w+w+w+w+'_'+w+w
        v52 = w+w+w+w+w+w+'_'+w
        v53 = w+w+w+w+w+w+w+y
        v54 = j+y+y+y+j+y
        v55 = w+w+j+j+w+j
        v56 = w+y+w+y+w+w
        v57 = y+j+j+j+j
        v58 = y+y+y+j+y
        v59 = w+w+w+j+w+w+w+w
        v60 = y+'_'+j+j+y
        v61 = y+j+j+'_'+y
        v62 = y+j+j+j+y+y
        v63 = y+j+j+j+y
        v64 = y+j+j+y+y+y+y
        v65 = y+y+w+y+w+y
        v66 = w+y+y+y+y+w
        v67 = y+y+y+y+w+w
        v68 = y+w+y+y+w+y
        v70 = w+y+y+y+y+y+w
        v72 = y+y+j+y+j+y+y
        v73 = y+'_'+j+'_'+w
        v74 = y+y+j+j+w
        v75 = y+y+j+j+j+j+y
        v76 = y+j+y+y+j+y+y
        v77 = y+y+y+y+j+j+j
        v78 = y+b+y+y+y+y+b
        v79 = y+j+y+y+y+y+j
        v80 = y+y+b+j+j
        v81 = 'vip'+b+z+o
        v82 = 'vip'+b+'_'+z
        v83 = y+y+w+j+j
        v84 = y+b+y+'_'+y 
        v88 = 'vip'+b+b+o
        v89 = y+j+y+j+'bot'
        v90 = y+y+j+b+b
        v91 = y+y+j+w+w
        
        ls = (v1,v2,v3,v4,v5,v6,v7,v8,v9,v10,v11,v12,v13,v14,v15,v16,v17,v18,
              v38,v39,v40,v41,v42,v43,v44,v45,v46,v47,v48,v49,v50,v51,v52,v53,
              v54,v55,v56,v57,v58,v59,v60,v61,v62,v63,v64,v65,v66,v67,v68,
              v70,v72,v73,v74,v75,v76,v77,v78,v79,v80,v81,v82,v83,v84,v88,v89,v90,v91)
        return random.choice(ls)

    async def generate_username_async(self):
        numb = 0
        print(f"{Colors.GREEN}🚀 بدء البحث عن اليوزرات...{Colors.RESET}")
        while self.is_running:
            try:
                user = self.usernameG()
                
                if user in self.filtered_usernames:
                    print(f"{Colors.YELLOW}-[{numb}] UserName is already filtered [@{user}]{Colors.RESET}")
                    numb += 1
                    continue

                # الفحص السريع عبر Fragment أولاً
                fragment_result = await self.Chack_UserName_Fragment_Async(user)
                
                if fragment_result == "Unavailable":
                    # إذا كان متاحاً على Fragment، نتحقق من التليجرام
                    await self.Chack_UserName_TeleGram(user)
                elif fragment_result == "taken":
                    print(f"{Colors.RED}-[{numb}] UserName is Taken [@{user}]{Colors.RESET}")
                    self.save_filtered_username(user, self.taken_file)
                elif fragment_result == "available": # Should be "Sold" based on your check
                    print(f"{Colors.YELLOW}-[{numb}] UserName is Sold [@{user}]{Colors.RESET}")
                else: # unknown
                    print(f"{Colors.MAGENTA}-[{numb}] UserName is unknown [@{user}]{Colors.RESET}")
                    self.save_filtered_username(user, self.unknown_file)
            
            except asyncio.CancelledError:
                print(f"{Colors.YELLOW}تم إيقاف مهمة الفحص.{Colors.RESET}")
                break # الخروج من الحلقة عند الإلغاء
            except Exception as e:
                print(f"{Colors.RED}An error occurred in the main loop: {e}{Colors.RESET}")

            numb += 1
            self.clicks += 1
            await asyncio.sleep(0.1)
        
        self.is_running = False # التأكد من تحديث الحالة عند الخروج من الحلقة

    async def Chack_UserName_Fragment_Async(self, user):
        """فحص Fragment بشكل غير متزامن"""
        try:
            url = f"https://fragment.com/username/{user}"
            async with self.session.get(url, timeout=3) as response:
                text = await response.text()
                
                if '<span class="tm-section-header-status tm-status-taken">Taken</span>' in text:
                    return "taken"
                elif '<span class="tm-section-header-status tm-status-unavail">Sold</span>' in text:
                    return "available" # This means sold on fragment
                elif '<div class="table-cell-status-thin thin-only tm-status-unavail">Unavailable</div>' in text:
                    return "Unavailable" # This is what we are looking for
                else:
                    return "unknown"
        except Exception:
            return "unknown"

    async def Chack_UserName_TeleGram(self, user):
        """فحص اليوزر على التليجرام"""
        try:
            tele = await self.client(CheckUsernameRequest(username=user))
            
            if tele:
                print(f"{Colors.GREEN}- UserName is Available (CheckUsernameRequest) [{user}]{Colors.RESET}")
                
                # فحص سريع للتأكد من عدم وجود حظر
                is_valid = await self.quick_advanced_check(user)
                
                if is_valid:
                    self.available_usernames.append(user)
                    
                    # التحقق إذا كان اليوزر مميزاً (3 أحرف أو أقل)
                    if len(user) <= 3:
                        self.premium_usernames.append(user)
                        print(f"{Colors.CYAN}🎉 تم العثور على يوزر مميز: @{user}{Colors.RESET}")
                    
                    # إنشاء القناة مباشرة
                    await self.save_username_to_channel(user)
                    
                    # إرسال إشعار
                    text = f"• New UserName Available.\n• UserName : @{user} ."
                    await self.client.send_message('me', text)
                else:
                    print(f"{Colors.RED}- UserName is Banned or Restricted [@{user}]{Colors.RESET}")
                    self.save_filtered_username(user, self.banned_file)
                      
        except errors.rpcbaseerrors.BadRequestError:
            print(f"{Colors.RED}- UserName is Band [@{user}]{Colors.RESET}")
            self.save_filtered_username(user, self.banned_file)
            return
        except errors.FloodWaitError as timer:
            num = int(timer.seconds)
            print(f"{Colors.RED}- Error Account Flood (CheckUsernameRequest) Time [{num}]\n- UserName [{user}]{Colors.RESET}")
            for i in range(num, 0, -1):
                print(f"{Colors.YELLOW}The flood will end after: [{i}]{Colors.RESET}", end="\r")
                await asyncio.sleep(1)
            return
        except errors.UsernameInvalidError:
            print(f"{Colors.RED}- UserName is Invalid [@{user}]{Colors.RESET}")
            self.save_filtered_username(user, self.invalid_file)
            return
        except Exception as e:
            print(f"{Colors.RED}- Error in Telegram check: {e} [@{user}]{Colors.RESET}")
            return

    async def quick_advanced_check(self, user):
        """فحص سريع للتأكد من أن اليوزر غير مبند"""
        try:
            await self.client.get_entity(user)
            return False
        except ValueError:
            return True
        except Exception:
            return True

    async def get_video_from_channel(self, user):
        """تحميل الفيديو من القناة"""
        try:
            video_channel = await self.client.get_entity('m23333')
            messages = await self.client.get_messages(video_channel, limit=5)
              
            for message in messages:
                if message.media and hasattr(message.media, 'document'):
                    for attr in message.media.document.attributes:
                        if isinstance(attr, types.DocumentAttributeVideo):
                            video_path = await self.client.download_media(message, file=f'Video_{user}.mp4')
                            print(f"{Colors.GREEN}- تم تحميل الفيديو بنجاح{Colors.RESET}")
                            return video_path
              
            print(f"{Colors.YELLOW}- لم يتم العثور على أي فيديو{Colors.RESET}")
            return None
              
        except Exception as e:
            print(f"{Colors.RED}- فشل في تحميل الفيديو: {e}{Colors.RESET}")
            return None

    async def save_username_to_channel(self, user):
        """حفظ اليوزر عن طريق إنشاء قناة"""
        try:
            # إنشاء القناة الجديدة
            r = await self.client(CreateChannelRequest(
                title=f"{user}",
                about=f"OWNER – @M_R_Q_P",
                megagroup=False
            ))
              
            new_channel = r.chats[0]
              
            # تعيين اليوزرنيم للقناة الجديدة
            try:
                await self.client(functions.channels.UpdateUsernameRequest(channel=new_channel, username=user))
                print(f"{Colors.GREEN}- تم تعيين اليوزرنيم @{user} للقناة بنجاح{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.RED}- فشل في تعيين اليوزرنيم: {e}{Colors.RESET}")
                return
              
            # الحصول على صورة القناة
            try:
                source_channel = await self.client.get_entity('rrkkkrr')
                photos = await self.client.get_profile_photos(source_channel, limit=1)
                if photos:
                    photo_path = await self.client.download_media(photos[0], file=f'channel_photo_{user}.jpg')
                    uploaded_file = await self.client.upload_file(photo_path)
                    input_photo = types.InputChatUploadedPhoto(file=uploaded_file)
                      
                    await self.client(EditPhotoRequest(
                        channel=new_channel,
                        photo=input_photo
                    ))
                    print(f"{Colors.GREEN}- تم تعيين صورة القناة بنجاح{Colors.RESET}")
                    os.remove(photo_path)
            # ... تكملة من حيث توقف الكود السابق
            except Exception as e:
                print(f"{Colors.YELLOW}- خطأ في تعيين صورة القناة: {e}{Colors.RESET}")
              
            # تحميل الفيديو من القناة
            video_path = await self.get_video_from_channel(user)
              
            bio_list = [" @m23333 ☘️"]
            bio = random.choice(bio_list)
              
            # إرسال الفيديو مع الترجمة إلى القناة الجديدة
            caption = (
                f'• ✧ ɴᴇᴡ ᴜsᴇʀ ✧  • [@{user}] .\n'
            )
              
            if video_path and os.path.exists(video_path):
                await self.client.send_file(new_channel, file=video_path, caption=caption)
                print(f"{Colors.GREEN}- تم إرسال الفيديو إلى القناة @{user}{Colors.RESET}")
            else:
                await self.client.send_message(new_channel, caption)
                print(f"{Colors.GREEN}- تم إرسال الرسالة إلى القناة @{user}{Colors.RESET}")
              
            # إرسال رسالة إضافية مع وقت المطالبة
            await self.client.send_message(new_channel, f' — Claim DataTime  - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
              
            # إرسال رسالة إلى المطور
            try:
                ra_aa_message = f"""• ✧ ɴᴇᴡ ᴜsᴇʀ ✧  • [@{user}] .
"""
                if video_path and os.path.exists(video_path):
                    await self.client.send_file(developer, video_path, caption=ra_aa_message)
                    print(f"{Colors.GREEN}- تم إرسال الفيديو إلى {developer}{Colors.RESET}")
                else:
                    await self.client.send_message(developer, ra_aa_message)
                    print(f"{Colors.GREEN}- تم إرسال الرسالة إلى {developer}{Colors.RESET}")
                      
            except Exception as e:
                print(f"{Colors.RED}- فشل في إرسال رسالة إلى {developer}: {e}{Colors.RESET}")
              
            # حذف الملف المؤقت
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
              
        except Exception as e:
            if "too many public channels" in str(e).lower():
                print(f"{Colors.RED}- Error (too many public channels) save_username_to_channel, UserName: [@{user}]\n Error : [{e}]{Colors.RESET}")
                await self.client.send_message('me', f"- Error (too many public channels) save_username_to_channel, UserName: [@{user}]\n- Error : [{e}]")
            elif "a wait" in str(e).lower() or "floodwaiterror" in str(e).lower():
                try:
                    time_flood = int(re.findall(r'\d+', str(e))[0])
                except:
                    time_flood = 60 # Default wait time
                print(f"{Colors.RED}- Error Account Flood (caused by UpdateUsernameRequest) Time [{time_flood}]\n- UserName [{user}]{Colors.RESET}")
                for i in range(time_flood, 0, -1):
                    print(f"{Colors.YELLOW}The flood will end after: [{i}]{Colors.RESET}", end="\r")
                    await asyncio.sleep(1)
            else:
                print(f"{Colors.RED}- Error save_username_to_channel, UserName: [@{user}]\n Error : [{e}]{Colors.RESET}")
                await self.client.send_message('me', f"- Error save_username_to_channel, UserName: [@{user}]\n- Error : [{e}]")

    async def run(self):
        
        os.makedirs("sessions", exist_ok=True)
        
        # تسجيل الدخول
        if not await self.login():
            return
        
        # إعداد معالج الأوامر
        self.setup_event_handler()
        
        # بدء جلسة aiohttp
        async with aiohttp.ClientSession() as session:
            self.session = session
            # إرسال رسالة للمستخدم للبدء
            await self.client.send_message('me', 'تم تشغيل البوت بنجاح. اكتب `.تشغيل` لبدء فحص اليوزرات.')
            # إبقاء البوت يعمل للاستماع للأوامر
            await self.client.run_until_disconnected()


async def main():
    """الدالة الرئيسية"""
    # تنظيف الشاشة
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # ... تكملة من حيث توقف الكود السابق

    
   
    client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
    
    bot = UltraUsernameClaimer(client)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print(f"\n{Colors.YELLOW}تم إيقاف البوت. إلى اللقاء!{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}حدث خطأ غير متوقع في المستوى الأعلى: {e}{Colors.RESET}")


    
    

