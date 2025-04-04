# curl -v -k -X POST -H "Content-Type: application/json" -H "Cache-Control: no-cache"  -d '{
# "update_id":10000,
# "callback_query":{
#   "id": "4382bfdwdsb323b2d9",
#   "from":{
#      "last_name":"Test Lastname",
#      "type": "private",
#      "id":1111111,
#      "first_name":"Test Firstname",
#      "username":"Testusername"
#   },
#   "data": "Data from button callback",
#   "inline_message_id": "1234csdbsk4839"
# }
# }' "https://YOUR.BOT.URL:YOURPORT/"


# curl -v -k -X POST -H "Content-Type: application/json" -H "Cache-Control: no-cache"  -d '{
# "update_id":10000,
# "message":{
#   "date":1441645532,
#   "chat":{
#      "last_name":"Test Lastname",
#      "id":194573162,
#      "type": "private",
#      "first_name":"Test Firstname",
#      "username":"quantum0"
#   },
#   "message_id":1365,
#   "from":{
#      "last_name":"Test Lastname",
#      "id":194573162,
#      "first_name":"Test Firstname",
#      "username":"quantum0", "is_bot":false
#   },
#   "text":"/start"
# }
# }' -H "X-Telegram-Bot-Api-Secret-Token: bnklgnbklgnfkbnkgfnbkfg" "https://ocrefbot.quantum0.ru/webhook"
