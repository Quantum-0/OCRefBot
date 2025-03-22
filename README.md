# OCRefBot
Inline Telegram Bot to store [Original Character Reference Sheet] for quick access for them
[![wakatime](https://wakatime.com/badge/user/7c9029ee-89d1-45a3-8197-cbf6c3bcaf78/project/679174e4-d656-4a2d-ad07-b9ccf47a3f63.svg)](https://wakatime.com/badge/user/7c9029ee-89d1-45a3-8197-cbf6c3bcaf78/project/679174e4-d656-4a2d-ad07-b9ccf47a3f63)

# TODO

- /settings - send only as file, send only as photo, send both
- /del_all
- /csv (dump db rows as csv)
- /dump_all (dumps all db as csv?) (only admin)

- black list of users!

- db creds to envs

- rework /help to less text and categories

- share with friend
- table [sharing]: user_id, friend_id, status
- meaning: friend_id will see user_id's gallery via bot
- status = requested, asked, cancelled, active
- /share_with @username - ask friend to add user's gallery
- /ask_for_share @username - friend ask user for seeing their gallery
