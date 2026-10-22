#!/usr/bin/env bash
BASE="http://localhost:8000"
RUN=$(date +%s)
EMAIL="test-$RUN@example.com"
USERNAME="tester_$RUN"
PASSWORD="Passw0rd123"


# Печатает заголовок, тело (красиво) и HTTP-код
call() {
  local title="$1"; shift
  echo; echo "=== $title"
  local out; out=$(curl -s -w "\n%{http_code}" "$@")
  echo "$out" | sed '$d' | jq . 2>/dev/null || echo "$out" | sed '$d'
  echo "HTTP $(echo "$out" | tail -n1)"
}

# Тихий вызов: возвращает только тело (для вытаскивания id/token)
quiet() { curl -s "$@"; }

check_id() {
  local name="$1"
  local value="$2"

  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    echo "ОШИБКА: $name имеет некорректный ID: '$value'"
    echo "Проверь ответ API и останови тесты."
    exit 1
  fi
}


# ---------- 1. Авторизация ----------
call "register" -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}"

# Вариант A: OAuth2 form (стандартный для FastAPI)
# TOKEN=$(quiet -X POST "$BASE/auth/login" \
#   -d "username=$EMAIL&password=$PASSWORD" | jq -r .access_token)
# Вариант B: JSON
TOKEN=$(quiet -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r .access_token)

echo "TOKEN: ${TOKEN:0:20}..."
AUTH=(-H "Authorization: Bearer $TOKEN")
JSON=(-H "Content-Type: application/json")

call "users/me" "$BASE/users/me" "${AUTH[@]}"

# ---------- 2. Теги ----------
TAG1=$(quiet -X POST "$BASE/tags" "${AUTH[@]}" "${JSON[@]}" \
  -d '{"name":"work","color":"#ff0000"}' | jq -r .id)
TAG2=$(quiet -X POST "$BASE/tags" "${AUTH[@]}" "${JSON[@]}" \
  -d '{"name":"home","color":"#00aa00"}' | jq -r .id)
check_id TAG1 "$TAG1"
check_id TAG2 "$TAG2"
echo "TAG1=$TAG1 TAG2=$TAG2"

call "tags: дубликат имени (ждём 409)" -X POST "$BASE/tags" "${AUTH[@]}" "${JSON[@]}" \
  -d '{"name":"work"}'

call "tags: невалидный цвет (ждём 422)" -X POST "$BASE/tags" "${AUTH[@]}" "${JSON[@]}" \
  -d '{"name":"x","color":"red"}'

call "tags: переименование" -X PATCH "$BASE/tags/$TAG2" "${AUTH[@]}" "${JSON[@]}" \
  -d '{"name":"family","color":"#0000ff"}'

call "tags: список" "$BASE/tags" "${AUTH[@]}"

# ---------- 3. Заметки ----------
NOTE=$(quiet -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d "{
  \"title\": \"Встреча с командой\",
  \"body\": \"Обсудить релиз\",
  \"starts_at\": \"2026-11-01T09:00:00Z\",
  \"tag_ids\": [$TAG1, $TAG2],
  \"reminders\": [10, 60],
  \"recurrence\": {\"freq\": \"weekly\", \"until\": \"2026-12-31\"}
}" | jq -r .id)
check_id NOTE "$NOTE"
echo "NOTE=$NOTE"

call "notes: создание (ждём 201, version=1)" -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d '{
  "title": "Простая заметка",
  "starts_at": "2026-11-05T12:00:00Z"
}'

call "notes: невалидное напоминание 5 мин (ждём 422)" -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d '{
  "title": "x", "starts_at": "2026-11-05T12:00:00Z", "reminders": [5]
}'

call "notes: дата без часового пояса (ждём 422)" -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d '{
  "title": "x", "starts_at": "2026-11-05T12:00:00"
}'

call "notes: until раньше начала (ждём 422)" -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d '{
  "title": "x", "starts_at": "2026-11-05T12:00:00Z",
  "recurrence": {"freq": "daily", "until": "2026-01-01"}
}'

call "notes: несуществующий тег (ждём 422)" -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d '{
  "title": "x", "starts_at": "2026-11-05T12:00:00Z", "tag_ids": [99999]
}'

call "notes: получить одну" "$BASE/notes/$NOTE" "${AUTH[@]}"

# ---------- 4. Версии и конфликты ----------
call "notes: PATCH title, version=1 (ждём version=2)" -X PATCH "$BASE/notes/$NOTE" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":1,"title":"Новый заголовок"}'

call "notes: PATCH со старой version=1 (ждём 409 + current)" -X PATCH "$BASE/notes/$NOTE" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":1,"title":"Чужая правка"}'

call "notes: PATCH только tag_ids (version должен вырасти до 3)" -X PATCH "$BASE/notes/$NOTE" \
  "${AUTH[@]}" "${JSON[@]}" -d "{\"version\":2,\"tag_ids\":[$TAG1]}"

call "notes: PATCH только reminders (version 4)" -X PATCH "$BASE/notes/$NOTE" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":3,"reminders":[60,1440]}'

call "notes: снять повтор (recurrence: null, version 5)" -X PATCH "$BASE/notes/$NOTE" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":4,"recurrence":null}'

call "notes: title=null (ждём 422)" -X PATCH "$BASE/notes/$NOTE" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":5,"title":null}'

# ---------- 5. Активация ----------
call "notes: deactivate (version 6)" -X POST "$BASE/notes/$NOTE/deactivate" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":5}'

call "notes: activate (version 7)" -X POST "$BASE/notes/$NOTE/activate" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":6}'

call "notes: activate со старой версией (ждём 409)" -X POST "$BASE/notes/$NOTE/activate" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":1}'


# ---------- Повторы и календарь ----------
SER=$(quiet -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d '{
  "title":"Зарядка","starts_at":"2026-11-02T09:00:00Z",
  "recurrence":{"freq":"daily","until":"2026-11-30"}}' | jq -r .id)
V() { quiet "$BASE/notes/$SER" "${AUTH[@]}" | jq .version; }
CAL() { quiet "$BASE/calendar?from=2026-11-02T00:00:00Z&to=2026-11-13T00:00:00Z" "${AUTH[@]}" \
        | jq -r --arg s "$SER" '.[] | select(.note_id==($s|tonumber) or .title=="Йога") | "\(.starts_at)  \(.title)"'; }

echo; echo "=== calendar: 11 дней серии (ждём 11 строк с 9:00 UTC)"; CAL

call "occurrence this: переименовать 5 ноября" -X PATCH \
  "$BASE/notes/$SER/occurrences/2026-11-05T09:00:00Z" "${AUTH[@]}" "${JSON[@]}" \
  -d "{\"scope\":\"this\",\"version\":$(V),\"title\":\"Зарядка (особая)\"}"

call "occurrence this: удалить 6 ноября (ждём 204)" -X DELETE \
  "$BASE/notes/$SER/occurrences/2026-11-06T09:00:00Z?scope=this&version=$(V)" "${AUTH[@]}"

call "occurrence this: перенести 7 ноября на 8-е 15:00" -X PATCH \
  "$BASE/notes/$SER/occurrences/2026-11-07T09:00:00Z" "${AUTH[@]}" "${JSON[@]}" \
  -d "{\"scope\":\"this\",\"version\":$(V),\"starts_at\":\"2026-11-08T15:00:00Z\"}"

echo; echo "=== calendar: 5-е переименовано, 6-го нет, 7-е на 8-е в 15:00"; CAL

call "occurrence: не на сетке (ждём 404)" -X PATCH \
  "$BASE/notes/$SER/occurrences/2026-11-05T10:00:00Z" "${AUTH[@]}" "${JSON[@]}" \
  -d "{\"scope\":\"this\",\"version\":$(V),\"title\":\"x\"}"

call "occurrence: старая версия (ждём 409)" -X PATCH \
  "$BASE/notes/$SER/occurrences/2026-11-05T09:00:00Z" "${AUTH[@]}" "${JSON[@]}" \
  -d '{"scope":"this","version":1,"title":"x"}'

call "occurrence following: с 10 ноября «Йога»" -X PATCH \
  "$BASE/notes/$SER/occurrences/2026-11-10T09:00:00Z" "${AUTH[@]}" "${JSON[@]}" \
  -d "{\"scope\":\"following\",\"version\":$(V),\"title\":\"Йога\"}"

echo; echo "=== calendar: до 9-го «Зарядка», с 10-го «Йога», прошлое не тронуто"; CAL

call "старая серия закончилась 9 ноября" "$BASE/notes/$SER" "${AUTH[@]}"
call "upcoming" "$BASE/upcoming" "${AUTH[@]}"
call "calendar: диапазон больше 100 дней (ждём 422)" \
  "$BASE/calendar?from=2026-01-01T00:00:00Z&to=2026-12-31T00:00:00Z" "${AUTH[@]}"


# ---------- 6. Корзина ----------
call "notes: удаление (ждём 204)" -X DELETE "$BASE/notes/$NOTE" "${AUTH[@]}"
call "notes: GET удалённой (ждём 404)" "$BASE/notes/$NOTE" "${AUTH[@]}"
call "notes: restore" -X POST "$BASE/notes/$NOTE/restore" "${AUTH[@]}"
call "notes: GET после restore (ждём 200)" "$BASE/notes/$NOTE" "${AUTH[@]}"

# ---------- 7. Теги и заметки ----------
call "tags: удаление тега (204)" -X DELETE "$BASE/tags/$TAG1" "${AUTH[@]}"
call "notes: тег исчез из заметки" "$BASE/notes/$NOTE" "${AUTH[@]}"

# ---------- 8. Изоляция пользователей ----------
call "без токена (ждём 401)" "$BASE/notes/$NOTE"



V=$(curl -s localhost:8000/notes/$NOTE -H "Authorization: Bearer $TOKEN" | jq .version)
for t in "A" "B"; do
  curl -s -o /dev/null -w "$t: %{http_code}\n" -X PATCH localhost:8000/notes/$NOTE \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"version\":$V,\"title\":\"правка $t\"}" &
done; wait


# ---------- 9. Изоляция пользователей ----------

echo
echo "=== Изоляция пользователей"

# Создаём тег от имени первого пользователя
TAG_PROBE=$(quiet -X POST "$BASE/tags" \
  "${AUTH[@]}" "${JSON[@]}" \
  -d '{"name":"isolation_probe","color":"#123456"}' | jq -r '.id')

check_id TAG_PROBE "$TAG_PROBE"
echo "TAG_PROBE=$TAG_PROBE"

# Регистрируем второго пользователя с уникальными данными
SUFFIX=$(date +%s)
EMAIL2="isolation-$SUFFIX@example.com"
USERNAME2="isolation_$SUFFIX"
PASSWORD2="Passw0rd123"

call "register user 2" -X POST "$BASE/auth/register" \
  "${JSON[@]}" \
  -d "{\"email\":\"$EMAIL2\",\"username\":\"$USERNAME2\",\"password\":\"$PASSWORD2\"}"

# Получаем токен второго пользователя
TOKEN2=$(quiet -X POST "$BASE/auth/login" \
  "${JSON[@]}" \
  -d "{\"email\":\"$EMAIL2\",\"password\":\"$PASSWORD2\"}" \
  | jq -r '.access_token')

if [[ -z "$TOKEN2" || "$TOKEN2" == "null" ]]; then
  echo "ОШИБКА: не удалось получить TOKEN2"
  exit 1
fi

AUTH2=(-H "Authorization: Bearer $TOKEN2")

# Второй пользователь не должен видеть заметку первого
call "user 2: GET чужой заметки (ждём 404)" \
  "$BASE/notes/$NOTE" "${AUTH2[@]}"

# Второй пользователь не должен изменять тег первого
call "user 2: PATCH чужого тега (ждём 404)" \
  -X PATCH "$BASE/tags/$TAG_PROBE" \
  "${AUTH2[@]}" "${JSON[@]}" \
  -d '{"name":"hacked_probe","color":"#123456"}'

# Второй пользователь не должен видеть заметку первого в общем списке
call "user 2: GET /notes (чужих заметок быть не должно)" \
  "$BASE/notes" "${AUTH2[@]}"

# Контроль: первый пользователь по-прежнему видит свою заметку
call "user 1: GET своей заметки (ждём 200)" \
  "$BASE/notes/$NOTE" "${AUTH[@]}"

# Контроль: тег первого пользователя не изменился
call "user 1: свой тег в списке" "$BASE/tags" "${AUTH[@]}"




LT=$(quiet -X POST "$BASE/tags" "${AUTH[@]}" "${JSON[@]}" -d '{"name":"list-tag"}' | jq -r .id)
quiet -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d "{
  \"title\":\"Уникальный Заголовок\",\"body\":\"100% готово\",
  \"starts_at\":\"2026-11-15T10:00:00Z\",\"tag_ids\":[$LT]}" >/dev/null

call "list: поиск по заголовку (ждём 1)" -G "$BASE/notes" --data-urlencode "q=уникальный" "${AUTH[@]}"
call "list: спецсимвол % (ждём 1, а не все)" "$BASE/notes?q=100%25" "${AUTH[@]}"
call "list: тег + активна (ждём 1)" "$BASE/notes?tag_ids=$LT&is_active=true" "${AUTH[@]}"
call "list: тег + неактивна (ждём 0)" "$BASE/notes?tag_ids=$LT&is_active=false" "${AUTH[@]}"
echo "=== list: сортировка по изменению ==="
call "list: сортировка по изменению" \
  "$BASE/notes?sort=updated_at&order=desc" "${AUTH[@]}"

echo
echo "=== list: вторая страница ==="
CUR=$(quiet "$BASE/notes?limit=1" "${AUTH[@]}" | jq -r '.next_cursor')

if [[ -n "$CUR" && "$CUR" != "null" ]]; then
  call "list: вторая страница" \
    "$BASE/notes?limit=1&cursor=$CUR" "${AUTH[@]}"
else
  echo "Пропущено: нет следующей страницы (нужно больше одной заметки)"
fi

echo
echo "=== list: битый cursor (ждём 400) ==="
call "list: битый cursor" "$BASE/notes?cursor=abc" "${AUTH[@]}"

echo
echo "=== list: неверный диапазон дат (ждём 422, если проверка добавлена) ==="
call "list: неверный диапазон дат" \
  "$BASE/notes?date_from=2026-11-30T00:00:00Z&date_to=2026-11-01T00:00:00Z" \
  "${AUTH[@]}"



ts() { python3 -c "from datetime import datetime,timedelta,timezone as z; print((datetime.now(z.utc)+timedelta(minutes=$1)).strftime('%Y-%m-%dT%H:%M:%SZ'))"; }
mk() { quiet -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d "{\"title\":\"$1\",\"starts_at\":\"$2\",\"is_active\":${3:-true}}" >/dev/null; }

mk "Скоро"        "$(ts 10)"
mk "Через 3 дня"  "$(ts 4320)"
mk "Прошло"       "$(ts -120)"
mk "Неактивная"   "$(ts -60)" false

echo; echo "=== upcoming (ждём: today=Скоро, week=Через 3 дня, past=Прошло, без Неактивной)"
quiet "$BASE/upcoming" "${AUTH[@]}" | jq '{today:[.today[].title], week:[.week[].title], past:[.past[].title]}'




echo; echo "=== reminders"
mk2() { quiet -X POST "$BASE/notes" "${AUTH[@]}" "${JSON[@]}" -d "$1" | jq -r .id; }

R1=$(mk2 "{\"title\":\"Напомни-10\",\"starts_at\":\"$(ts 11)\",\"reminders\":[10]}")
R2=$(mk2 "{\"title\":\"Неактивная-напоминание\",\"starts_at\":\"$(ts 11)\",\"reminders\":[10],\"is_active\":false}")
R3=$(mk2 "{\"title\":\"Удалённая-напоминание\",\"starts_at\":\"$(ts 11)\",\"reminders\":[10]}")
call "удалить R3" -X DELETE "$BASE/notes/$R3" "${AUTH[@]}"

echo "Жду 100 секунд..."; sleep 100
echo "--- ждём ровно одно уведомление «Напомни-10»"
quiet "$BASE/notifications" "${AUTH[@]}" | jq '[.[] | .title]'

curl -s localhost:8025/api/v1/messages | jq '[.messages[] | .Subject]'


# ---------- Тест 2: отметка «показано» ----------
echo; echo "=== notifications: seen"
NID=$(quiet "$BASE/notifications?unseen=true" "${AUTH[@]}" \
  | jq -r '[.[] | select(.title=="Напомни-10")][0].id')

if [ -z "$NID" ] || [ "$NID" = "null" ]; then
  echo "ОШИБКА: уведомление «Напомни-10» не найдено, проверка seen пропущена"
else
  call "seen: отметить (ждём 204)" -X POST "$BASE/notifications/$NID/seen" "${AUTH[@]}"

  echo "--- в unseen после seen (ждём false)"
  quiet "$BASE/notifications?unseen=true" "${AUTH[@]}" \
    | jq --argjson id "$NID" 'any(.[]; .id == $id)'

  echo "--- в полном списке остаётся (ждём true)"
  quiet "$BASE/notifications?unseen=false" "${AUTH[@]}" \
    | jq --argjson id "$NID" 'any(.[]; .id == $id)'

  call "seen: повторно (идемпотентно, ждём 204)" -X POST "$BASE/notifications/$NID/seen" "${AUTH[@]}"
  call "seen: несуществующее (ждём 404)" -X POST "$BASE/notifications/999999999/seen" "${AUTH[@]}"
fi

# ---------- Тест 3: активация до срока возвращает напоминание ----------
echo; echo "=== activation: напоминание возвращается после активации"
# Обе заметки неактивны, старт через 12 минут, напоминание за 10 (срок через ~2 минуты)
ACT=$(mk2 "{\"title\":\"Активируем-до-срока\",\"starts_at\":\"$(ts 12)\",\"reminders\":[10],\"is_active\":false}")
CTL=$(mk2 "{\"title\":\"Контроль-неактивная\",\"starts_at\":\"$(ts 12)\",\"reminders\":[10],\"is_active\":false}")
echo "ACT=$ACT CTL=$CTL"

call "activate до срока (ждём is_active=true)" -X POST "$BASE/notes/$ACT/activate" \
  "${AUTH[@]}" "${JSON[@]}" -d '{"version":1}'

echo "Жду 150 секунд (срок через ~2 минуты + тик 15 секунд)..."; sleep 150

echo "--- уведомления: ждём «Активируем-до-срока», без «Контроль-неактивная»"
quiet "$BASE/notifications?unseen=false" "${AUTH[@]}" | jq '[.[] | .title]'

echo "--- письма: ждём «Напоминание: Активируем-до-срока», без «Контроль-неактивная»"
curl -s localhost:8025/api/v1/messages | jq '[.messages[] | .Subject]'

echo; echo "=== SSE"
TK1=$(quiet -X POST "$BASE/events/token" "${AUTH[@]}" | jq -r .token)
TK2=$(quiet -X POST "$BASE/events/token" "${AUTH[@]}" | jq -r .token)
TKX=$(quiet -X POST "$BASE/events/token" -H "Authorization: Bearer $TOKEN2" | jq -r .token)
rm -f /tmp/sse_a.txt /tmp/sse_b.txt /tmp/sse_x.txt
curl -sN "$BASE/events?token=$TK1" > /tmp/sse_a.txt & P1=$!
curl -sN "$BASE/events?token=$TK2" > /tmp/sse_b.txt & P2=$!
curl -sN "$BASE/events?token=$TKX" > /tmp/sse_x.txt & P3=$!
sleep 1

call "sse: плохой токен (ждём 401)" "$BASE/events?token=bad"

SN=$(mk2 '{"title":"SSE-заметка","starts_at":"2026-12-01T10:00:00Z"}')
V=$(quiet "$BASE/notes/$SN" "${AUTH[@]}" | jq .version)
quiet -X PATCH "$BASE/notes/$SN" "${AUTH[@]}" "${JSON[@]}" \
  -d "{\"version\":$V,\"title\":\"SSE правка\"}" >/dev/null
quiet -X DELETE "$BASE/notes/$SN" "${AUTH[@]}" >/dev/null
sleep 1
kill $P1 $P2 $P3 2>/dev/null

echo "--- вкладка A (ждём hello, note.created, note.updated, note.deleted)"
grep '^event:' /tmp/sse_a.txt
echo "--- вкладка B (те же события)"
grep '^event:' /tmp/sse_b.txt
echo "--- чужой пользователь (ждём только hello)"
grep '^event:' /tmp/sse_x.txt


echo; echo "=== settings"
call "settings: плохой пояс (ждём 422)" -X PATCH "$BASE/users/me" "${AUTH[@]}" "${JSON[@]}" \
  -d '{"timezone":"Mars/Olympus"}'
call "settings: смена пояса" -X PATCH "$BASE/users/me" "${AUTH[@]}" "${JSON[@]}" \
  -d '{"timezone":"Asia/Bishkek"}'
OTHER="dup-$RUN@example.com"
quiet -X POST "$BASE/auth/register" "${JSON[@]}" \
  -d "{\"email\":\"$OTHER\",\"username\":\"dup_$RUN\",\"password\":\"$PASSWORD\"}" >/dev/null
call "settings: занятый email (ждём 409)" -X PATCH "$BASE/users/me" "${AUTH[@]}" "${JSON[@]}" \
  -d "{\"email\":\"$OTHER\"}"
call "settings: свой новый email" -X PATCH "$BASE/users/me" "${AUTH[@]}" "${JSON[@]}" \
  -d "{\"email\":\"new-$RUN@example.com\"}"

echo; echo "=== trash"
T1=$(mk2 '{"title":"Корзина-1","starts_at":"2026-12-01T10:00:00Z"}')
T2=$(mk2 '{"title":"Корзина-2","starts_at":"2026-12-01T10:00:00Z","reminders":[10]}')
T3=$(mk2 '{"title":"Корзина-3","starts_at":"2026-12-01T10:00:00Z"}')
for id in $T1 $T2 $T3; do quiet -X DELETE "$BASE/notes/$id" "${AUTH[@]}" >/dev/null; done

echo "--- корзина (ждём 3-2-1, новые первыми)"
quiet "$BASE/trash" "${AUTH[@]}" | jq '[.items[].title]'
echo "--- пагинация: limit=1, затем вторая страница (ждём Корзина-3, Корзина-2)"
quiet "$BASE/trash?limit=1" "${AUTH[@]}" | jq '[.items[].title, .next_cursor != null]'
CUR=$(quiet "$BASE/trash?limit=1" "${AUTH[@]}" | jq -r .next_cursor)
quiet -G "$BASE/trash" --data-urlencode "limit=1" --data-urlencode "cursor=$CUR" "${AUTH[@]}" | jq '[.items[].title]'

call "restore из корзины" -X POST "$BASE/notes/$T1/restore" "${AUTH[@]}"
echo "--- в корзине осталось (ждём Корзина-3, Корзина-2)"
quiet "$BASE/trash" "${AUTH[@]}" | jq '[.items[].title]'

call "чужой пользователь удаляет навсегда (ждём 404)" -X DELETE "$BASE/trash/$T3" \
  -H "Authorization: Bearer $TOKEN2"
call "удалить навсегда (ждём 204)" -X DELETE "$BASE/trash/$T2" "${AUTH[@]}"
call "повторно (ждём 404)" -X DELETE "$BASE/trash/$T2" "${AUTH[@]}"
call "живую заметку так не удалить (ждём 404)" -X DELETE "$BASE/trash/$T1" "${AUTH[@]}"
call "очистить корзину (ждём 204)" -X DELETE "$BASE/trash" "${AUTH[@]}"
echo "--- корзина пуста (ждём [])"
quiet "$BASE/trash" "${AUTH[@]}" | jq '[.items[].title]'


echo; echo "Готово."


