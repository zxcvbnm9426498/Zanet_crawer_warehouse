# 知乎爬虫 CSV 字段说明文档

本文档详细说明了知乎爬虫输出的三个 CSV 文件中所有字段的中英文映射和说明。

---

## 1. 创作者信息表 (creators_*.csv)

| 字段名 (Field Name) | 中文名称 | 数据类型 | 说明 |
|-------------------|---------|---------|------|
| `user_id` | 用户ID | String | 知乎用户的唯一标识符 |
| `user_link` | 用户主页链接 | String | 用户主页的完整URL |
| `user_nickname` | 用户昵称 | String | 用户在知乎上显示的昵称 |
| `user_avatar` | 用户头像 | String | 用户头像图片的URL地址 |
| `url_token` | URL标识符 | String | 用户主页URL中的标识符（如：zhangkangkang） |
| `gender` | 性别 | String | 用户性别：男/女/未知 |
| `ip_location` | IP属地 | String | 用户IP属地信息（如：IP 属地河南） |
| `follows` | 关注数 | Integer | 用户关注的人数 |
| `fans` | 粉丝数 | Integer | 关注该用户的粉丝数量 |
| `anwser_count` | 回答数 | Integer | 用户发布的回答总数 |
| `video_count` | 视频数 | Integer | 用户发布的视频总数 |
| `question_count` | 提问数 | Integer | 用户提出的问题总数 |
| `article_count` | 文章数 | Integer | 用户发布的文章总数 |
| `column_count` | 专栏数 | Integer | 用户创建的专栏总数 |
| `get_voteup_count` | 获得赞同数 | Integer | 用户所有内容获得的赞同总数 |
| `last_modify_ts` | 最后修改时间戳 | Integer | 数据最后更新的时间戳（13位毫秒时间戳） |

---

## 2. 内容信息表 (contents_*.csv)

内容表包含回答、文章、视频和想法四种类型的内容，通过 `content_type` 字段区分。

| 字段名 (Field Name) | 中文名称 | 数据类型 | 说明 |
|-------------------|---------|---------|------|
| `content_id` | 内容ID | String | 内容的唯一标识符 |
| `content_type` | 内容类型 | String | 内容类型：`answer`(回答) / `article`(文章) / `zvideo`(视频) / `pin`(想法) |
| `content_text` | 内容文本 | String | 内容的完整文本（视频类型可能为空，想法包含文本和图片URL） |
| `question_id` | 问题ID | String | 问题ID（仅回答类型有值，其他类型为空） |
| `content_url` | 内容链接 | String | 内容的完整URL地址 |
| `title` | 标题 | String | 内容标题（想法类型为空） |
| `desc` | 描述 | String | 内容描述/摘要 |
| `created_time` | 创建时间 | Integer | 内容创建时间戳（Unix时间戳，秒） |
| `updated_time` | 更新时间 | Integer | 内容最后更新时间戳（Unix时间戳，秒） |
| `voteup_count` | 赞同数 | Integer | 内容获得的赞同数量 |
| `comment_count` | 评论数 | Integer | 内容的评论总数 |
| `user_id` | 作者ID | String | 内容作者的唯一标识符 |
| `user_link` | 作者主页链接 | String | 内容作者主页的完整URL |
| `user_nickname` | 作者昵称 | String | 内容作者在知乎上显示的昵称 |
| `user_avatar` | 作者头像 | String | 内容作者头像图片的URL地址 |
| `user_url_token` | 作者URL标识符 | String | 内容作者主页URL中的标识符 |
| `source_keyword` | 来源关键词 | String | 来源关键词（creator/detail模式为空，search模式有值） |
| `last_modify_ts` | 最后修改时间戳 | Integer | 数据最后更新的时间戳（13位毫秒时间戳） |

### 内容类型说明

- **answer (回答)**: 用户对问题的回答，包含 `question_id` 字段
- **article (文章)**: 用户发布的文章，通常有标题和完整内容
- **zvideo (视频)**: 用户发布的视频，`content_text` 可能为空
- **pin (想法)**: 用户发布的想法，可能包含文本和图片，`title` 为空

---

## 3. 评论信息表 (comments_*.csv)

评论表包含所有内容的评论数据，通过 `content_type` 和 `content_id` 关联到对应的内容。

| 字段名 (Field Name) | 中文名称 | 数据类型 | 说明 |
|-------------------|---------|---------|------|
| `comment_id` | 评论ID | String | 评论的唯一标识符 |
| `parent_comment_id` | 父评论ID | String | 父评论的ID（一级评论为空，二级评论有值） |
| `content` | 评论内容 | String | 评论的完整文本内容 |
| `publish_time` | 发布时间 | Integer | 评论发布时间戳（Unix时间戳，秒） |
| `ip_location` | IP属地 | String | 评论者的IP属地信息 |
| `sub_comment_count` | 子评论数 | Integer | 该评论下的子评论数量 |
| `like_count` | 点赞数 | Integer | 评论获得的点赞数量 |
| `dislike_count` | 踩数 | Integer | 评论获得的踩数量 |
| `content_id` | 内容ID | String | 评论所属内容的ID |
| `content_type` | 内容类型 | String | 评论所属内容的类型：`answer` / `article` / `zvideo` / `pin` |
| `user_id` | 评论者ID | String | 评论者的唯一标识符 |
| `user_link` | 评论者主页链接 | String | 评论者主页的完整URL |
| `user_nickname` | 评论者昵称 | String | 评论者在知乎上显示的昵称 |
| `user_avatar` | 评论者头像 | String | 评论者头像图片的URL地址 |
| `user_url_token` | 评论者URL标识符 | String | 评论者主页URL中的标识符 |

### 评论层级说明

- **一级评论**: `parent_comment_id` 为空，直接评论内容
- **二级评论**: `parent_comment_id` 有值，回复一级评论或其他二级评论

---

## 数据关系说明

### 表之间的关联关系

1. **creators ↔ contents**: 通过 `user_id` 或 `user_url_token` 关联
2. **contents ↔ comments**: 通过 `content_id` 和 `content_type` 关联
3. **comments 内部**: 通过 `parent_comment_id` 关联父子评论关系

### 数据示例

**创作者表 (creators)**
```
user_id: df4deb9232dab1f6f7193041b6628da0
user_nickname: 张抗抗
url_token: zhangkangkang
```

**内容表 (contents)**
```
content_id: 1972348983276986402
content_type: answer
user_id: df4deb9232dab1f6f7193041b6628da0
question_id: 1971950440536085490
```

**评论表 (comments)**
```
comment_id: 1234567890
content_id: 1972348983276986402
content_type: answer
parent_comment_id: (空，表示一级评论)
user_id: abc123...
```

---

## 注意事项

1. **时间戳格式**:
   - `created_time`, `updated_time`, `publish_time`: Unix时间戳（秒）
   - `last_modify_ts`: 毫秒时间戳（13位）

2. **空值处理**:
   - 空字符串 `""` 表示该字段无值
   - 数字类型字段为 `0` 表示无值

3. **内容类型**:
   - 通过 `content_type` 字段区分不同类型的内容
   - 不同类型的内容某些字段可能为空（如想法的 `title` 为空）

4. **编码格式**:
   - CSV文件使用 UTF-8 编码（带BOM），可直接用Excel打开

---

## 文件命名规则

- **creators_YYYYMMDD_HHMMSS.csv**: 创作者信息
- **contents_YYYYMMDD_HHMMSS.csv**: 内容信息（回答/文章/视频/想法）
- **comments_YYYYMMDD_HHMMSS.csv**: 评论信息

其中 `YYYYMMDD_HHMMSS` 为爬取开始的时间戳。

