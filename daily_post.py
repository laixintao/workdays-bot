# -*- coding: utf-8 -*-

import tweepy
import arrow

import logging
from collections import namedtuple


logging.basicConfig(level=logging.DEBUG)
holidays_2018 = (
    # from http://www.gov.cn/zhengce/content/2017-11/30/content_5243579.htm
    ("01-01", "元旦"),
    ("02-15", "春节"),
    ("02-16", "春节"),
    ("02-17", "春节"),
    ("02-18", "春节"),
    ("02-19", "春节"),
    ("02-20", "春节"),
    ("02-21", "春节"),
    ("04-05", "清明节"),
    ("04-06", "清明节"),
    ("04-07", "清明节"),
    ("04-29", "劳动节"),
    ("04-30", "劳动节"),
    ("05-01", "劳动节"),
    ("06-18", "端午节"),
    ("09-24", "中秋节"),
    ("10-01", "国庆节"),
    ("10-02", "国庆节"),
    ("10-03", "国庆节"),
    ("10-04", "国庆节"),
    ("10-05", "国庆节"),
    ("10-06", "国庆节"),
    ("10-07", "国庆节"),
)
work_weekends_data = (
    # weekend bou you need to work
    "02-11",
    "02-24",
    "04-08",
    "04-28",
    "09-29",
    "09-30",
)

WORKDAYS_TEMPLATE = "今天是工作日，距离休息还有{next_rest_left}天"
WEEKENDS_TEMPLATE = "今天是{day_type}，好好休息。距离上班还有{next_work}天.全年假日还剩{weekends_left}天。"


with open("secret") as secret_file:
    key, secret, token, token_secret = [line.strip() for line in secret_file.readlines()]
CONSUMERKEY, CONSUMERSECRET, ACCESSTOKEN, ACCESSTOKENSECRET = key, secret, token, token_secret


def get_api():
    auth = tweepy.OAuthHandler(CONSUMERKEY, CONSUMERSECRET)
    auth.set_access_token(ACCESSTOKEN, ACCESSTOKENSECRET)
    api = tweepy.API(auth)
    return api


def get_holidays():
    """return all holidays of this year"""
    Holiday = namedtuple("Holiday", "name arrow")
    holidays = []
    for holiday_data in holidays_2018:
        name = holiday_data[1]
        date = arrow.get(holiday_data[0], "MM-DD", tzinfo='Asia/Shanghai').replace(year=arrow.now().year)
        holidays.append(Holiday(name, date))
    return holidays

def get_work_weekends():
    """Weekends but you work"""
    work_weekends = [arrow.get(work_weekend, "MM-DD", tzinfo='Asia/Shanghai').replace(year=arrow.now().year)
                     for work_weekend in work_weekends_data]
    return work_weekends

work_weekends = get_work_weekends()
holidays = get_holidays()


def get_day_type(arrow_day):
    for holiday in holidays:
        if holiday.arrow == arrow_day:
            return holiday.name, False
    for work_day in work_weekends:
        if work_day == arrow_day:
            return '工作日', True
    week_day = arrow_day.weekday()
    if week_day == 6 or week_day == 5:
        return '周末', False
    return '工作日', True


def get_year_calendar():
    first_day = arrow.get("2000-01-01", "YYYY-MM-DD", tzinfo="Asia/Shanghai").replace(year=arrow.now().year)
    last_day = arrow.get("2000-12-31", "YYYY-MM-DD", tzinfo="Asia/Shanghai").replace(year=arrow.now().year)
    all_days = last_day - first_day
    Day = namedtuple("Day", "name arrow is_workday")
    result = []
    logging.debug("{}, {}".format(first_day, last_day))
    for day in arrow.Arrow.range('day', first_day, last_day):
        _t, _is_workday = get_day_type(day)
        result.append(Day(_t, day, _is_workday))
    return result


year_calendar = get_year_calendar()


def get_next_workday_or_weekend(today):
    """
    :param today: Day namedtuple
    """
    count = 0
    start_counting =False
    target_is_workday = False
    for day in year_calendar:
        if day.arrow == today.arrow:
            start_counting = True
            target_is_workday = not today.is_workday
        if start_counting:
            if day.is_workday == target_is_workday:
                return count
            count += 1
    return 0


def get_workday_map(day_arrow):
    """Draw a map of workdays"""
    workdays_spend = 0
    workdays_left = 0
    weekends_spend = 0
    weekends_left = 0
    spent = True
    current_month = 0
    workday_map = ["" for _ in range(13)]
    for day in year_calendar:
        if day.arrow == day_arrow:
            spent = False
            workday_map[day.arrow.month] += 'x'
        elif spent:
            if day.is_workday:
                workdays_spend += 1
                workday_map[day.arrow.month] += 'x'
            else:
                weekends_spend += 1
        else:
            if day.is_workday:
                workdays_left += 1
                workday_map[day.arrow.month] += 'o'
            else:
                weekends_left += 1
    return workdays_spend, workdays_left, weekends_spend, weekends_left, workday_map


def make_tweet(day):
    day_type = ""
    next_count = 0
    message = ""
    workdays_spend, workdays_left, weekends_spend, weekends_left, workdays_map = get_workday_map(day.arrow)
    count = get_next_workday_or_weekend(day)

    if day.is_workday:
        message = "\n".join(workdays_map[1:])
    else:
        message = WEEKENDS_TEMPLATE.format(day_type=day.name,
                                           next_work=count,
                                           weekends_left=weekends_left)
    return message


def daily_post():
    today = arrow.get(arrow.now().format('YYYY-MM-DD'), 'YYYY-MM-DD', tzinfo='Asia/Shanghai')
    for day in year_calendar:
        if day.arrow == today:
            tweet = make_tweet(day)
            break
    else:
        raise Exception("Today not in year_calendar")
    logging.info("Tweet: {}, length: {}".format(tweet, len(tweet)))
    api = get_api()
    result = api.update_status(tweet[:280])
    logging.info(result)


if __name__ == '__main__':
    daily_post()
