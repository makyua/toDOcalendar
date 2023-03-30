#数字の表示をわかりやすく
def money_format(int):
    # 単位
    base = ["万", "億", "兆"]
    # 挿入するために逆順にした方が都合がよい
    res = str(int)[::-1]
    # 単位を入れる回数に注意
    for i in range((len(res)-1)//4):
        place = (i+1)*4+i
        # 今回はスライスで対応、ほかにリストにしてから挿入するなど
        res = res[:place]+base[i]+res[place:]
    return res[::-1]