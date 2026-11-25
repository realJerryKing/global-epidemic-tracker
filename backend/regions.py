"""Curated six-digit mainland administrative codes, not a full county gazetteer."""
REGIONS = {}


def add(code, name, parent, level):
    REGIONS[code] = dict(code=code, name=name, parent_code=parent, level=level)


add('000000', '全国', None, 'country')
for pair in '''11 北京市;12 天津市;13 河北省;14 山西省;15 内蒙古自治区;21 辽宁省;22 吉林省;23 黑龙江省;31 上海市;32 江苏省;33 浙江省;34 安徽省;35 福建省;36 江西省;37 山东省;41 河南省;42 湖北省;43 湖南省;44 广东省;45 广西壮族自治区;46 海南省;50 重庆市;51 四川省;52 贵州省;53 云南省;54 西藏自治区;61 陕西省;62 甘肃省;63 青海省;64 宁夏回族自治区;65 新疆维吾尔自治区'''.split(';'):
    prefix, name = pair.split()
    add(prefix + '0000', name, '000000', 'province')

for prefix, name, children in [
    ('1101', '北京市辖区', '01 东城区;02 西城区;05 朝阳区;06 丰台区;07 石景山区;08 海淀区;09 门头沟区;11 房山区;12 通州区;13 顺义区;14 昌平区;15 大兴区;16 怀柔区;17 平谷区;18 密云区;19 延庆区'),
    ('4401', '广州市', '03 荔湾区;04 越秀区;05 海珠区;06 天河区;11 白云区;12 黄埔区;13 番禺区;14 花都区;15 南沙区;17 从化区;18 增城区'),
]:
    add(prefix + '00', name, prefix[:2] + '0000', 'city')
    for pair in children.split(';'):
        suffix, name = pair.split()
        add(prefix + suffix, name, prefix + '00', 'district')


def ancestry(code):
    while code is not None:
        yield code
        code = REGIONS[code]['parent_code']
