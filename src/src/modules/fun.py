"""
娱乐模块~ 和小南一起玩吧！(｡･ω･｡)ﾉ♡
"""
import logging
import random
import json
import os
from datetime import datetime, date

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from .base_module import BaseModule

logger = logging.getLogger(__name__)

# 数据文件路径
FUN_DATA_FILE = "data/fun_data.json"


def _load_fun_data():
    """加载娱乐数据~"""
    if os.path.exists(FUN_DATA_FILE):
        try:
            with open(FUN_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"pet": {}, "minesweeper": {}, "blackjack": {}}


def _save_fun_data(data):
    """保存娱乐数据~"""
    os.makedirs(os.path.dirname(FUN_DATA_FILE), exist_ok=True)
    with open(FUN_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class Fun(BaseModule):
    """娱乐模块~ 和小南一起玩游戏！"""
    
    name = "fun"
    description = "和小南一起玩~"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
    
    def register_handlers(self, application):
        """注册娱乐命令~"""
        application.add_handler(CommandHandler("dice", self.dice))
        application.add_handler(CommandHandler("rps", self.rps))
        application.add_handler(CommandHandler("fortune", self.fortune))
        application.add_handler(CommandHandler("lottery", self.lottery))
        application.add_handler(CommandHandler("choose", self.choose))
        application.add_handler(CommandHandler("pet", self.pet))
        application.add_handler(CommandHandler("minesweeper", self.minesweeper))
        application.add_handler(CommandHandler("blackjack", self.blackjack))
        application.add_handler(CommandHandler("truth_or_dare", self.truth_or_dare))
        application.add_handler(CommandHandler("meme", self.meme))
        application.add_handler(CommandHandler("compliment", self.compliment))
        application.add_handler(CommandHandler("insult", self.insult))
        application.add_handler(CommandHandler("coin", self.coin))
        application.add_handler(CommandHandler("8ball", self.eight_ball))
        application.add_handler(CommandHandler("horoscope", self.horoscope))
    
    def _random_emoji(self):
        """随机返回一个可爱表情~"""
        emojis = ["✨", "🌟", "⭐", "💫", "🌈", "🎀", "🌸", "💝", "🎵", "🎶", "🍀", "🌺", "🦋", "🎐", "💗", "💖", "✨", "🌟"]
        return random.choice(emojis)
    
    def _random_greeting(self):
        """随机问候语~"""
        greetings = [
            "小南来啦~", "喵呜~", "嘿嘿~", "来啦来啦~",
            "小南在呢~", "呜呼呼~", "嗨嗨~", "到！"
        ]
        return random.choice(greetings)
    
    async def dice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/dice - 掷骰子喵～"""
        max_sides = 100
        
        if context.args:
            try:
                max_sides = int(context.args[0])
                if max_sides < 2:
                    max_sides = 2
                elif max_sides > 1000:
                    max_sides = 1000
            except ValueError:
                pass
        
        result = random.randint(1, max_sides)
        
        reactions = {
            "最高": ["🎉 哇塞！", "🌟 天哪！", "🎊 太棒了！", "🏆 无敌！"],
            "高": ["✨ 不错哦~", "👍 挺好的！", "😊 可以可以！", "💪 继续加油！"],
            "中": ["🤔 还行吧~", "😐 一般般~", "🙂 凑合~", "🤷 就这样~"],
            "低": ["😅 哎呀…", "😰 呜…", "😢 好可惜…", "😭 不是吧…"],
            "最低": ["😂 这也太惨了！", "😆 哈哈哈对不起！", "🤣 小南忍不住笑了！", "😅 运气守恒定律~"]
        }
        
        if result == max_sides:
            reaction = random.choice(reactions["最高"])
        elif result >= max_sides * 0.8:
            reaction = random.choice(reactions["高"])
        elif result >= max_sides * 0.3:
            reaction = random.choice(reactions["中"])
        elif result > 1:
            reaction = random.choice(reactions["低"])
        else:
            reaction = random.choice(reactions["最低"])
        
        extras = [
            f"小南的幸运数字是{random.randint(1, max_sides)}，差一点就中了！",
            f"今天适合{random.choice(['吃火锅', '喝奶茶', '看电影', '睡懒觉', '出去浪'])}哦~",
            f"小南掐指一算，下次一定能出{random.randint(1, max_sides)}！",
            f"这个数字在{random.choice(['数学', '物理', '化学', '玄学'])}上有着特殊的意义！",
            f"你知道吗？{result}是{random.choice(['质数', '偶数', '奇数', '完全平方数'])}哦~"
        ]
        
        if max_sides == 2:
            result_text = "正面" if result == 1 else "反面"
            await update.message.reply_text(
                f"🪙 {self._random_greeting()}\n"
                f"硬币飞起来啦~ 转啊转~\n"
                f"🎯 {result_text}！{reaction}\n"
                f"{random.choice(extras)}"
            )
        else:
            await update.message.reply_text(
                f"🎲 {self._random_greeting()}\n"
                f"骰子骨碌碌地滚了起来~\n"
                f"🎯 {result}/{max_sides}！{reaction}\n"
                f"{random.choice(extras)}"
            )
    
    async def rps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/rps - 猜拳喵～"""
        choices = {"石头": "✊", "剪刀": "✌️", "布": "🖐️"}
        rules = {"石头": "剪刀", "剪刀": "布", "布": "石头"}
        
        if not context.args:
            taunts = [
                "来嘛来嘛~ 小南手都痒了！",
                "不敢来吗？怕输给小南？😝",
                "猜拳猜拳！小南要赢你！",
                "石头剪刀布~ 小南最拿手了！"
            ]
            await update.message.reply_text(
                f"🎮 {random.choice(taunts)}\n"
                f"✊ 石头  ✌️ 剪刀  🖐️ 布\n"
                f"出招吧：/rps 石头"
            )
            return
        
        user_choice = context.args[0]
        choice_map = {
            "石头": "石头", "石": "石头", "rock": "石头",
            "剪刀": "剪刀", "剪": "剪刀", "scissors": "剪刀",
            "布": "布", "paper": "布"
        }
        
        user_choice = choice_map.get(user_choice.lower(), None)
        if not user_choice:
            await update.message.reply_text(
                f"😅 要出石头、剪刀或布哦~\n"
                f"小南等你重新出招：/rps 石头"
            )
            return
        
        bot_choice = random.choice(list(choices.keys()))
        
        win_msgs = [
            "🎉 你赢啦！小南好不甘心！再来！",
            "🎊 厉害厉害！小南佩服！",
            "🏆 你太强了！小南认输！",
            "🌟 哇！你赢了！小南要加油了！"
        ]
        lose_msgs = [
            "😝 小南赢啦！你还要再练练哦~",
            "🎉 耶！小南赢了！再来一局！",
            "😊 小南的胜利！承让承让~",
            "💪 小南果然是最强的！"
        ]
        draw_msgs = [
            "🤝 平局！我们真是心有灵犀！",
            "😯 一样！再来再来！",
            "🤔 这都能一样？再来一局！",
            "😲 不是吧？又平局？"
        ]
        
        if user_choice == bot_choice:
            result = random.choice(draw_msgs)
        elif rules[user_choice] == bot_choice:
            result = random.choice(win_msgs)
        else:
            result = random.choice(lose_msgs)
        
        extras = [
            f"小南刚才偷偷{random.choice(['看了攻略', '练习了一晚上', '拜了师', '许了愿'])}，但还是输了…",
            f"你知道吗？猜拳的{random.choice(['历史', '起源', '概率', '心理学'])}很有意思哦~",
            f"小南觉得你{random.choice(['今天运气很好', '很有天赋', '偷偷练过', '开挂了'])}！",
            f"下次小南要用{random.choice(['超级秘密武器', '终极必杀技', '隐藏绝招', '独门秘籍'])}！"
        ]
        
        await update.message.reply_text(
            f"🎮 猜拳！\n"
            f"你：{choices[user_choice]} {user_choice}\n"
            f"小南：{choices[bot_choice]} {bot_choice}\n"
            f"{result}\n"
            f"{random.choice(extras)}"
        )
    
    async def fortune(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/fortune - 今日运势喵～"""
        user = update.effective_user
        user_name = user.first_name or "小可爱"
        
        ranks = ["🌟 大吉", "⭐ 吉", "✨ 中吉", "☀️ 小吉", "🌤️ 末吉", "🌧️ 凶", "⛈️ 大凶"]
        weights = [15, 25, 25, 20, 10, 4, 1]
        
        seed = datetime.now().strftime("%Y%m%d") + str(user.id)
        random.seed(seed)
        rank = random.choices(ranks, weights=weights, k=1)[0]
        random.seed()
        
        descs = {
            "🌟 大吉": [
                "今天运气爆棚！去买彩票吧！",
                "宇宙都在帮你！做什么都能成！",
                "今天是你的幸运日！冲鸭！",
                "好运挡都挡不住！"
            ],
            "⭐ 吉": [
                "今天是个好日子，适合表白哦~",
                "阳光正好，微风不燥，今天不错！",
                "适合尝试新事物，会有惊喜！",
                "今天会遇到好事，要保持微笑~"
            ],
            "✨ 中吉": [
                "平平淡淡才是真，今天也不错~",
                "会有小惊喜等着你，留意身边哦~",
                "今天适合和朋友聚聚~",
                "随遇而安，今天会很舒服~"
            ],
            "☀️ 小吉": [
                "小小的幸运在靠近你~",
                "今天可能会收到好消息！",
                "适合出去走走，会有偶遇~",
                "今天的小确幸在等着你~"
            ],
            "🌤️ 末吉": [
                "可能会有小波折，但都能解决~",
                "今天要耐心一点哦~",
                "小麻烦而已，别担心~",
                "风雨过后会有彩虹~"
            ],
            "🌧️ 凶": [
                "今天要小心说话，避免误会~",
                "别担心，小南会陪着你的！",
                "今天适合宅在家里~",
                "小心行事，一切都会好的~"
            ],
            "⛈️ 大凶": [
                "呜… 今天最好哪都别去…",
                "小南给你抱抱！今天要小心！",
                "今天宜睡觉，忌出门~",
                "别怕！小南会保护你的！"
            ]
        }
        
        desc = random.choice(descs[rank])
        
        items = ["🐱 小猫", "🍀 四叶草", "🌈 彩虹", "🌟 星星", "🎀 蝴蝶结", "🌸 樱花", "🍰 蛋糕", "☕ 热可可", "🎵 音乐", "📚 书本", "🎮 游戏", "🧸 小熊", "🌺 花", "🦋 蝴蝶", "🎐 风铃", "🍦 冰淇淋", "🎪 马戏团", "🎠 旋转木马"]
        colors = ["粉色 💗", "蓝色 💙", "紫色 💜", "红色 ❤️", "绿色 💚", "黄色 💛", "白色 🤍", "橙色 🧡", "金色 💛", "银色 🤍"]
        
        lucky_item = random.choice(items)
        lucky_color = random.choice(colors)
        
        tips = [
            f"今天适合穿{lucky_color}的衣服哦~",
            f"带上{lucky_item}会带来好运！",
            f"小南建议你今天{random.choice(['多喝水', '早点睡', '吃顿好的', '听听音乐', '出去走走'])}~",
            f"今天的幸运数字是{random.randint(1, 99)}！",
            f"今天宜{random.choice(['表白', '购物', '学习', '运动', '发呆'])}，忌{random.choice(['熬夜', '生气', '冲动', '懒惰'])}~"
        ]
        
        await update.message.reply_text(
            f"🔮 {user_name} 的今日运势\n"
            f"{self._random_emoji()} 运势：{rank}\n"
            f"💬 {desc}\n"
            f"🍀 幸运物：{lucky_item}\n"
            f"🎨 幸运色：{lucky_color}\n"
            f"💡 {random.choice(tips)}\n"
            f"小南会一直陪着你的~ {self._random_emoji()}"
        )
    
    async def lottery(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/lottery - 抽签喵～"""
        user = update.effective_user
        user_name = user.first_name or "小可爱"
        
        ranks = ["🎉 大吉", "⭐ 吉", "✨ 中吉", "☀️ 小吉", "🌤️ 末吉", "🌧️ 凶", "⛈️ 大凶"]
        weights = [10, 20, 25, 25, 15, 4, 1]
        
        seed = datetime.now().strftime("%Y%m%d") + str(user.id)
        random.seed(seed)
        rank = random.choices(ranks, weights=weights, k=1)[0]
        random.seed()
        
        poems = {
            "🎉 大吉": ["春风得意马蹄疾，一日看尽长安花", "长风破浪会有时，直挂云帆济沧海", "会当凌绝顶，一览众山小"],
            "⭐ 吉": ["海内存知己，天涯若比邻", "但愿人长久，千里共婵娟", "桃花潭水深千尺，不及汪伦送我情"],
            "✨ 中吉": ["花开堪折直须折，莫待无花空折枝", "人生得意须尽欢，莫使金樽空对月", "此情可待成追忆，只是当时已惘然"],
            "☀️ 小吉": ["小荷才露尖尖角，早有蜻蜓立上头", "春色满园关不住，一枝红杏出墙来", "等闲识得东风面，万紫千红总是春"],
            "🌤️ 末吉": ["沉舟侧畔千帆过，病树前头万木春", "山重水复疑无路，柳暗花明又一村", "天生我材必有用，千金散尽还复来"],
            "🌧️ 凶": ["屋漏偏逢连夜雨，船迟又遇打头风", "抽刀断水水更流，举杯消愁愁更愁", "问君能有几多愁，恰似一江春水向东流"],
            "⛈️ 大凶": ["黑云翻墨未遮山，白雨跳珠乱入船", "风萧萧兮易水寒，壮士一去兮不复还", "无可奈何花落去，似曾相识燕归来"]
        }
        
        poem = random.choice(poems[rank])
        
        fortunes = [
            f"小南掐指一算，{user_name}今天会遇到好事~",
            f"这个签说明{user_name}最近运气不错！",
            f"小南觉得{user_name}今天要开心哦~",
            f"这个签的意思是… 嗯… 天机不可泄露！",
            f"小南偷偷告诉你，这个签其实很准的！"
        ]
        
        await update.message.reply_text(
            f"🎋 {user_name} 抽到了{rank}\n"
            f"📜 签文：{poem}\n"
            f"💬 {random.choice(fortunes)}\n"
            f"{self._random_emoji()} 小南祝你今天开开心心的~"
        )
    
    async def choose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/choose - 选择困难症救星喵～"""
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                f"🤔 {random.choice(['选择困难症犯了吗？', '纠结了吧？', '选不出来了吧？', '让小南来帮你！'])}\n"
                f"用法：/choose 选项1 选项2 [选项3...]\n"
                f"例如：/choose 火锅 烧烤 奶茶"
            )
            return
        
        choices = context.args
        chosen = random.choice(choices)
        
        reasons = [
            f"这个看起来最好吃！", f"小南觉得这个最适合你~",
            f"命运在向你招手哦！", f"就决定是你了！",
            f"这个！这个！选这个！", f"小南掐指一算，就是这个了！",
            f"听小南的准没错~", f"这个运气最好！",
            f"小南的直觉告诉我是这个！", f"这个选项在闪闪发光呢~",
            f"小南偷偷投了这个一票！", f"这个！不接受反驳！"
        ]
        
        reactions = [
            f"🎯 就它了！",
            f"✨ 小南推荐这个！",
            f"💫 选这个准没错！",
            f"🌟 这个！这个！",
            f"⭐ 小南选了这个！"
        ]
        
        await update.message.reply_text(
            f"🤔 {random.choice(['让小南想想…', '嗯… 让小南算算…', '小南在思考…', '掐指一算…'])}\n"
            f"选项：{'、'.join(choices)}\n"
            f"{random.choice(reactions)} {chosen}\n"
            f"理由：{random.choice(reasons)}\n"
            f"{random.choice(['不用谢~', '小南很擅长这个！', '下次纠结还来找小南！', '小南的选择困难症治疗术怎么样？'])}"
        )
    
    async def pet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/pet - 养一只小南的虚拟宠物喵～"""
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name or "小可爱"
        
        data = _load_fun_data()
        pet_data = data["pet"]
        
        if user_id not in pet_data:
            pet_types = ["🐱 小猫咪", "🐶 小狗狗", "🐰 小兔子", "🐼 小熊猫", "🦊 小狐狸", "🐸 小青蛙", "🐻 小熊", "🐯 小老虎", "🦁 小狮子"]
            pet_type = random.choice(pet_types)
            pet_data[user_id] = {
                "name": f"{user_name}的{pet_type}",
                "type": pet_type,
                "hunger": 100,
                "happiness": 100,
                "energy": 100,
                "birthday": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            _save_fun_data(data)
            
            welcomes = [
                f"🎉 {pet_type} 从蛋里孵出来啦！",
                f"🎊 恭喜{user_name}获得{pet_type}一只！",
                f"✨ {pet_type} 选择了你作为主人！",
                f"🎉 缘分到了！{pet_type}来到了你身边！"
            ]
            
            await update.message.reply_text(
                f"{random.choice(welcomes)}\n"
                f"🎂 生日：{pet_data[user_id]['birthday']}\n"
                f"要好好照顾它哦~\n"
                f"/pet - 查看状态\n"
                f"/pet feed - 喂食\n"
                f"/pet play - 玩耍\n"
                f"/pet sleep - 睡觉"
            )
            return
        
        pet = pet_data[user_id]
        
        if context.args:
            action = context.args[0].lower()
            
            if action == "feed":
                pet["hunger"] = min(100, pet["hunger"] + 30)
                pet["happiness"] = min(100, pet["happiness"] + 10)
                _save_fun_data(data)
                
                foods = ["小鱼干", "肉肉", "零食", "罐头", "水果", "饼干"]
                food = random.choice(foods)
                
                reacts = [
                    f"{pet['name']} 开心地吃起了{food}！",
                    f"{pet['name']} 吃得吧唧吧唧的~",
                    f"{pet['name']} 表示{food}很好吃！",
                    f"{pet['name']} 吃完还舔了舔嘴巴~"
                ]
                
                await update.message.reply_text(
                    f"🍽️ 喂食~\n"
                    f"{random.choice(reacts)}\n"
                    f"饱腹：{pet['hunger']}/100  开心：{pet['happiness']}/100"
                )
                
            elif action == "play":
                if pet["energy"] < 20:
                    await update.message.reply_text(
                        f"😴 {pet['name']} 太累了，眼睛都睁不开了~\n"
                        f"让它睡觉吧：/pet sleep"
                    )
                    return
                pet["energy"] = max(0, pet["energy"] - 20)
                pet["happiness"] = min(100, pet["happiness"] + 25)
                pet["hunger"] = max(0, pet["hunger"] - 15)
                _save_fun_data(data)
                
                games = ["捉迷藏", "扔球球", "跳圈圈", "追尾巴", "爬树", "游泳", "跑步", "跳舞"]
                game = random.choice(games)
                
                reacts = [
                    f"{pet['name']} 玩{game}玩得好开心！",
                    f"{pet['name']} 在{game}中展现了惊人的天赋！",
                    f"{pet['name']} 拉着你一起玩{game}~",
                    f"{pet['name']} 玩{game}玩到停不下来！"
                ]
                
                await update.message.reply_text(
                    f"🎾 玩耍~\n"
                    f"{random.choice(reacts)}\n"
                    f"开心：{pet['happiness']}/100  精力：{pet['energy']}/100  饱腹：{pet['hunger']}/100"
                )
                
            elif action == "sleep":
                pet["energy"] = min(100, pet["energy"] + 40)
                pet["hunger"] = max(0, pet["hunger"] - 10)
                _save_fun_data(data)
                
                reacts = [
                    f"{pet['name']} 蜷成一团睡着了~ zzzZZZ",
                    f"{pet['name']} 打着小呼噜~ zzzZZZ",
                    f"{pet['name']} 睡梦中还在笑~ zzzZZZ",
                    f"{pet['name']} 抱着尾巴睡着了~ zzzZZZ"
                ]
                
                await update.message.reply_text(
                    f"💤 睡觉~\n"
                    f"{random.choice(reacts)}\n"
                    f"精力恢复到了：{pet['energy']}/100"
                )
            else:
                await update.message.reply_text(
                    f"😅 不知道要做什么呢~\n"
                    f"试试：/pet feed /pet play /pet sleep"
                )
            return
        
        status = "😊" if pet["happiness"] > 60 else "😐" if pet["happiness"] > 30 else "😢"
        hunger = "🍖" if pet["hunger"] > 60 else "🍗" if pet["hunger"] > 30 else "😫"
        energy = "⚡" if pet["energy"] > 60 else "🔋" if pet["energy"] > 30 else "😴"
        
        mood_text = "很开心" if pet["happiness"] > 60 else "一般" if pet["happiness"] > 30 else "不开心"
        hunger_text = "吃饱了" if pet["hunger"] > 60 else "有点饿" if pet["hunger"] > 30 else "好饿"
        energy_text = "活力满满" if pet["energy"] > 60 else "有点累" if pet["energy"] > 30 else "好困"
        
        await update.message.reply_text(
            f"🏠 {pet['name']}\n"
            f"{status} 心情：{mood_text}\n"
            f"{hunger} 饱腹：{hunger_text}\n"
            f"{energy} 精力：{energy_text}\n"
            f"🎂 {pet['birthday']}\n"
            f"/pet feed | play | sleep"
        )
    
    async def minesweeper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/minesweeper - 扫雷小游戏喵～"""
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name or "小可爱"
        
        data = _load_fun_data()
        game_data = data["minesweeper"]
        
        if context.args and context.args[0] == "new":
            size = 5
            mines = 5
            
            board = [[0 for _ in range(size)] for _ in range(size)]
            mine_positions = random.sample(range(size * size), mines)
            
            for pos in mine_positions:
                r, c = divmod(pos, size)
                board[r][c] = -1
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < size and 0 <= nc < size and board[nr][nc] != -1:
                            board[nr][nc] += 1
            
            game_data[user_id] = {
                "board": board,
                "revealed": [[False for _ in range(size)] for _ in range(size)],
                "size": size,
                "mines": mines,
                "game_over": False
            }
            _save_fun_data(data)
            
            await update.message.reply_text(
                f"💣 扫雷开始！\n"
                f"{size}x{size} 棋盘，{mines} 颗雷\n"
                f"小心别踩到哦~\n"
                f"/minesweeper open 行 列 - 翻开\n"
                f"例如：/minesweeper open 1 2（范围 0-{size-1}）"
            )
            return
        
        if context.args and context.args[0] == "open" and len(context.args) >= 3:
            if user_id not in game_data:
                await update.message.reply_text("😅 还没有游戏~ 用 /minesweeper new 开始吧！")
                return
            
            game = game_data[user_id]
            if game["game_over"]:
                await update.message.reply_text("💥 游戏结束了~ 用 /minesweeper new 重新开始吧！")
                return
            
            try:
                r, c = int(context.args[1]), int(context.args[2])
            except:
                await update.message.reply_text("😅 格式不对~ 例如：/minesweeper open 1 2")
                return
            
            if not (0 <= r < game["size"] and 0 <= c < game["size"]):
                await update.message.reply_text(f"😅 坐标范围是 0 到 {game['size']-1}")
                return
            
            if game["revealed"][r][c]:
                await update.message.reply_text("😅 已经翻开啦~")
                return
            
            if game["board"][r][c] == -1:
                game["game_over"] = True
                _save_fun_data(data)
                boom_msgs = [
                    f"💥 BOOOOM！{user_name} 踩到地雷啦！",
                    f"💥 轰！{user_name} 被炸飞了~",
                    f"💥 哎呀！{user_name} 踩雷了！",
                    f"💥 地雷爆炸！{user_name} 游戏结束~"
                ]
                await update.message.reply_text(f"{random.choice(boom_msgs)}")
                return
            
            game["revealed"][r][c] = True
            _save_fun_data(data)
            
            total_cells = game["size"] * game["size"]
            revealed_count = sum(sum(row) for row in game["revealed"])
            if revealed_count == total_cells - game["mines"]:
                game["game_over"] = True
                _save_fun_data(data)
                win_msgs = [
                    f"🎉 恭喜通关！{user_name} 太厉害了！👏",
                    f"🎊 {user_name} 成功扫除了所有地雷！天才！",
                    f"🏆 {user_name} 是扫雷大师！",
                    f"🌟 完美通关！{user_name} 好棒！"
                ]
                await update.message.reply_text(f"{random.choice(win_msgs)}")
                return
            
            value = game["board"][r][c]
            emoji = "⬜" if value == 0 else f"{value}️⃣"
            
            safe_msgs = [
                f"🔍 安全！({r},{c}) 是{emoji}",
                f"✅ 还好不是雷~ ({r},{c}) = {emoji}",
                f"😌 虚惊一场~ ({r},{c}) 是{emoji}",
                f"✨ 运气不错！({r},{c}) = {emoji}"
            ]
            
            await update.message.reply_text(
                f"{random.choice(safe_msgs)}\n"
                f"进度：{revealed_count}/{total_cells - game['mines']}"
            )
            return
        
        await update.message.reply_text(
            f"💣 扫雷小游戏\n"
            f"/minesweeper new - 新游戏\n"
            f"/minesweeper open 行 列 - 翻开格子"
        )
    
    async def blackjack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/blackjack - 21点小游戏喵～"""
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name or "小可爱"
        
        data = _load_fun_data()
        game_data = data["blackjack"]
        
        def draw_card():
            cards = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
            return random.choice(cards)
        
        def calc_hand(hand):
            total = 0
            aces = 0
            for card in hand:
                if card in ["J", "Q", "K"]:
                    total += 10
                elif card == "A":
                    aces += 1
                    total += 11
                else:
                    total += int(card)
            while total > 21 and aces > 0:
                total -= 10
                aces -= 1
            return total
        
        def hand_to_str(hand):
            return " ".join(hand)
        
        if context.args and context.args[0] == "new":
            player_hand = [draw_card(), draw_card()]
            dealer_hand = [draw_card(), draw_card()]
            
            game_data[user_id] = {
                "player": player_hand,
                "dealer": dealer_hand,
                "game_over": False
            }
            _save_fun_data(data)
            
            player_total = calc_hand(player_hand)
            
            if player_total == 21:
                game_data[user_id]["game_over"] = True
                _save_fun_data(data)
                await update.message.reply_text(
                    f"🃏 天胡开局！{user_name} 直接21点！\n"
                    f"🎉 赢啦！小南都惊呆了！"
                )
                return
            
            await update.message.reply_text(
                f"🃏 21点开始~\n"
                f"你的牌：{hand_to_str(player_hand)} = {player_total}\n"
                f"庄家牌：{hand_to_str(dealer_hand[:1])} + ?\n"
                f"/blackjack hit - 要牌  /blackjack stand - 停牌"
            )
            return
        
        if context.args and context.args[0] == "hit":
            if user_id not in game_data or game_data[user_id]["game_over"]:
                await update.message.reply_text("😅 没有进行中的游戏~ 用 /blackjack new 开始吧！")
                return
            
            game = game_data[user_id]
            game["player"].append(draw_card())
            player_total = calc_hand(game["player"])
            
            if player_total > 21:
                game["game_over"] = True
                _save_fun_data(data)
                await update.message.reply_text(
                    f"💥 爆牌啦！\n"
                    f"你的牌：{hand_to_str(game['player'])} = {player_total}\n"
                    f"庄家牌：{hand_to_str(game['dealer'])} = {calc_hand(game['dealer'])}\n"
                    f"小南赢啦~ 再来一局吧！"
                )
                return
            
            _save_fun_data(data)
            await update.message.reply_text(
                f"🃏 要牌~\n"
                f"你的牌：{hand_to_str(game['player'])} = {player_total}\n"
                f"/blackjack hit - 继续要牌  /blackjack stand - 停牌"
            )
            return
        
        if context.args and context.args[0] == "stand":
            if user_id not in game_data or game_data[user_id]["game_over"]:
                await update.message.reply_text("😅 没有进行中的游戏~ 用 /blackjack new 开始吧！")
                return
            
            game = game_data[user_id]
            game["game_over"] = True
            
            while calc_hand(game["dealer"]) < 17:
                game["dealer"].append(draw_card())
            
            player_total = calc_hand(game["player"])
            dealer_total = calc_hand(game["dealer"])
            
            _save_fun_data(data)
            
            if dealer_total > 21:
                result = f"🎉 庄家爆牌！{user_name} 赢啦！"
            elif player_total > dealer_total:
                result = f"🎉 {user_name} 赢啦！"
            elif player_total == dealer_total:
                result = "🤝 平局！"
            else:
                result = "😅 庄家赢了~ 再来一局吧！"
            
            await update.message.reply_text(
                f"🃏 游戏结束~\n"
                f"你的牌：{hand_to_str(game['player'])} = {player_total}\n"
                f"庄家牌：{hand_to_str(game['dealer'])} = {dealer_total}\n"
                f"{result}"
            )
            return
        
        await update.message.reply_text(
            f"🃏 21点小游戏\n"
            f"/blackjack new - 新游戏\n"
            f"/blackjack hit - 要牌\n"
            f"/blackjack stand - 停牌"
        )
    
    async def truth_or_dare(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/truth_or_dare - 真心话大冒险喵～"""
        if not context.args:
            await update.message.reply_text(
                f"🎭 真心话大冒险~\n"
                f"/truth_or_dare truth - 真心话\n"
                f"/truth_or_dare dare - 大冒险"
            )
            return
        
        mode = context.args[0].lower()
        
        truth_questions = [
            "你最近一次说谎是什么时候？", "你最尴尬的经历是什么？",
            "你偷偷喜欢过谁？", "你做过最疯狂的事情是什么？",
            "你最害怕什么？", "你最大的秘密是什么？",
            "你最后悔的事情是什么？", "你做过最丢脸的事情是什么？",
            "你最想实现的愿望是什么？", "你曾经偷偷哭过吗？",
            "你最想回到过去的哪个时刻？", "你觉得自己最大的缺点是什么？"
        ]
        
        dare_challenges = [
            "对身边的人说一句「我爱你」！", "模仿一种动物的叫声！",
            "做10个俯卧撑！", "用唱歌的方式说话！",
            "闭着眼睛转3圈！", "学企鹅走路10秒！",
            "用方言说一段话！", "做20个深蹲！",
            "模仿一个明星！", "学猫叫三声！",
            "跳一段舞！", "对着镜子做鬼脸！"
        ]
        
        if mode == "truth":
            question = random.choice(truth_questions)
            await update.message.reply_text(
                f"🎭 真心话~\n"
                f"问题：{question}\n"
                f"要老实回答哦~ (｡•̀ᴗ-)✧"
            )
        elif mode == "dare":
            challenge = random.choice(dare_challenges)
            await update.message.reply_text(
                f"🎭 大冒险~\n"
                f"挑战：{challenge}\n"
                f"敢不敢接受？(｀∀´)Ψ"
            )
        else:
            await update.message.reply_text("😅 要用 truth 或 dare 哦~")
    
    async def meme(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/meme - 小南的冷笑话喵～"""
        memes = [
            ("🐱", "为什么猫不喜欢玩扑克？", "因为总有老鼠在偷看！"),
            ("🐶", "狗为什么喜欢追尾巴？", "因为它想抓住自己的把柄！"),
            ("🐔", "为什么鸡要过马路？", "因为它想去对面找鸭聊天！"),
            ("🐧", "企鹅为什么不能飞？", "因为它们怕撞到冰山！"),
            ("🐼", "熊猫为什么有黑眼圈？", "因为它熬夜吃竹子！"),
            ("🦊", "狐狸为什么那么狡猾？", "因为它每天都在想恶作剧！"),
            ("🐰", "兔子为什么不吃窝边草？", "因为它要留着装饰房间！"),
            ("🐷", "猪为什么总是哼哼？", "因为它忘记歌词了！"),
            ("🦁", "狮子为什么是百兽之王？", "因为它有最帅的头发！"),
            ("🐘", "大象为什么怕老鼠？", "因为老鼠会偷它的花生！"),
            ("🦒", "长颈鹿为什么脖子那么长？", "因为它想看更远的风景！"),
            ("🦋", "蝴蝶为什么那么漂亮？", "因为它每天都在打扮自己！"),
            ("🐌", "蜗牛为什么走得慢？", "因为它背着房子旅行呢！")
        ]
        
        emoji, question, punchline = random.choice(memes)
        
        await update.message.reply_text(
            f"😄 小南的冷笑话~\n\n"
            f"🤔 {emoji} {question}\n\n"
            f"💡 {punchline}\n\n"
            f"喵哈哈哈~ (｡ˇ‸ˇ｡)"
        )
    
    async def compliment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/compliment - 小南夸夸你喵～"""
        user_name = update.effective_user.first_name or "小可爱"
        
        compliments = [
            f"{user_name} 今天看起来特别可爱呢！",
            f"{user_name} 的笑容比阳光还要温暖~",
            f"小南觉得 {user_name} 是最棒的人！",
            f"{user_name} 让这个世界变得更美好了~",
            f"哇！{user_name} 今天超有魅力的！",
            f"{user_name} 的眼睛里有星星在闪烁~",
            f"小南最喜欢 {user_name} 了！",
            f"{user_name} 真的很特别，独一无二！",
            f"今天也是为 {user_name} 打call的一天！",
            f"{user_name} 就像小太阳一样温暖~",
            f"小南觉得 {user_name} 做什么都很厉害！",
            f"能和 {user_name} 聊天，小南好开心~",
            f"{user_name} 的品味真的很好呢！",
            f"小南想和 {user_name} 做一辈子的好朋友！"
        ]
        
        compliment = random.choice(compliments)
        
        await update.message.reply_text(
            f"💝 小南夸夸你~\n\n"
            f"🌟 {compliment}\n\n"
            f"要开心哦！(｡♥‿♥｡)"
        )
    
    async def insult(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/insult - 小南的傲娇模式喵～"""
        user_name = update.effective_user.first_name or "小可爱"
        
        insults = [
            f"哼！{user_name} 今天又偷懒了吧！",
            f"{user_name} 是个大笨蛋！… 不过小南不讨厌笨蛋啦~",
            f"呜… {user_name} 欺负小南！",
            f"哼！才不是特意为 {user_name} 准备的呢！",
            f"{user_name} 好烦哦… 但是小南不讨厌你啦！",
            f"笨蛋 {user_name}！… 不过小南就喜欢笨蛋~",
            f"哼！小南才没有在等 {user_name} 呢！",
            f"{user_name} 真是的… 让人家这么担心！",
            f"笨蛋！小南才没有很想 {user_name} 呢！",
            f"{user_name} 这个迟钝鬼！… 但是小南原谅你啦~",
            f"哼！{user_name} 以为这样就能讨好小南吗？… 好吧可以！",
            f"{user_name} 真是拿你没办法呢… 小南认输啦！"
        ]
        
        insult = random.choice(insults)
        
        await update.message.reply_text(
            f"😤 哼！\n\n"
            f"💬 {insult}\n\n"
            f"才不是特意为你准备的呢！(｀へ´)"
        )
    
    async def coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/coin - 抛硬币喵～"""
        result = random.choice(["正面", "反面"])
        
        await update.message.reply_text(
            f"🪙 抛硬币~\n"
            f"硬币旋转中…\n"
            f"🎯 结果是：{result}！"
        )
    
    async def eight_ball(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/8ball - 魔法8球喵～"""
        if not context.args:
            await update.message.reply_text(
                f"🔮 魔法8球~\n"
                f"问小南一个问题吧！\n"
                f"用法：/8ball 你的问题"
            )
            return
        
        question = " ".join(context.args)
        
        answers = [
            "🎯 当然可以！小南觉得没问题~",
            "⭐ 很有可能哦！",
            "✨ 小南掐指一算，答案是肯定的！",
            "🌟 是的！小南也这么觉得~",
            "💫 毫无疑问！",
            "🌙 小南觉得可以试试看~",
            "☀️ 今天运气不错，应该可以的！",
            "🌈 小南的直觉告诉我是好的结果！",
            "🌧️ 可能不太行哦…",
            "☁️ 小南觉得还是不要比较好~",
            "🌪️ 答案是否定的…",
            "❄️ 不太可能呢…",
            "💭 小南也说不准呢~",
            "🤔 再问一次吧，小南没听清楚~",
            "😅 这个问题太难了，小南答不上来…",
            "🔮 天机不可泄露！",
            "🎠 小南觉得你心里已经有答案了！"
        ]
        
        answer = random.choice(answers)
        
        await update.message.reply_text(
            f"🔮 魔法8球~\n\n"
            f"❓ {question}\n\n"
            f"💬 {answer}"
        )
    
    async def horoscope(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/horoscope - 星座运势喵～"""
        zodiacs = {
            "白羊座": "♈", "金牛座": "♉", "双子座": "♊", "巨蟹座": "♋",
            "狮子座": "♌", "处女座": "♍", "天秤座": "♎", "天蝎座": "♏",
            "射手座": "♐", "摩羯座": "♑", "水瓶座": "♒", "双鱼座": "♓"
        }
        
        if not context.args:
            await update.message.reply_text(
                f"⭐ 星座运势~\n"
                f"用法：/horoscope 星座名称\n"
                f"例如：/horoscope 白羊座"
            )
            return
        
        user_zodiac = context.args[0]
        
        matched_zodiac = None
        for name in zodiacs:
            if name.startswith(user_zodiac) or user_zodiac.startswith(name):
                matched_zodiac = name
                break
        
        if not matched_zodiac:
            await update.message.reply_text(
                "😅 没有找到这个星座呢~\n"
                "试试：白羊座、金牛座、双子座、巨蟹座、狮子座、处女座、\n"
                "天秤座、天蝎座、射手座、摩羯座、水瓶座、双鱼座"
            )
            return
        
        zodiac_emoji = zodiacs[matched_zodiac]
        
        horoscopes = [
            ("🌟", "大吉", "今天运势超好！适合表白、约会、购物~"),
            ("⭐", "吉", "平平淡淡才是真，今天适合学习新东西！"),
            ("✨", "中吉", "会有小惊喜等着你，要保持微笑哦~"),
            ("☀️", "小吉", "今天适合和朋友一起玩，会很快乐的！"),
            ("🌤️", "末吉", "可能会有点小麻烦，但都能解决的~"),
            ("🌧️", "凶", "今天要小心说话，避免误会哦~"),
            ("⛈️", "大凶", "呜… 今天最好待在家里休息呢…")
        ]
        
        seed = datetime.now().strftime("%Y%m%d") + matched_zodiac
        random.seed(seed)
        rank_emoji, rank_name, desc = random.choice(horoscopes)
        random.seed()
        
        await update.message.reply_text(
            f"⭐ {matched_zodiac}今日运势\n"
            f"{zodiac_emoji} 运势：{rank_emoji} {rank_name}\n"
            f"解读：{desc}\n"
            f"小南祝你今天开开心心的~ ✨"
        )
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return (
            "/dice - 掷骰子\n"
            "/rps - 猜拳\n"
            "/fortune - 今日运势\n"
            "/lottery - 抽签\n"
            "/choose - 选择困难症救星\n"
            "/pet - 养宠物\n"
            "/minesweeper - 扫雷\n"
            "/blackjack - 21点\n"
            "/truth_or_dare - 真心话大冒险\n"
            "/meme - 冷笑话\n"
            "/compliment - 夸夸\n"
            "/insult - 傲娇\n"
            "/coin - 抛硬币\n"
            "/8ball - 魔法8球\n"
            "/horoscope - 星座运势"
        )
