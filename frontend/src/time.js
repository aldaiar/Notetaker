import { DateTime } from 'luxon'

// Все моменты времени хранятся и передаются в UTC, а показываются в поясе пользователя.

const LOCAL_FMT = "yyyy-LL-dd'T'HH:mm"

/** ISO (UTC) -> значение для <input type="datetime-local"> в поясе tz */
export function toLocalInput(iso, tz) {
  return DateTime.fromISO(iso, { zone: 'utc' }).setZone(tz).toFormat(LOCAL_FMT)
}

/** значение <input type="datetime-local"> в поясе tz -> ISO UTC с суффиксом Z */
export function fromLocalInput(value, tz) {
  const dt = DateTime.fromFormat(value, LOCAL_FMT, { zone: tz })
  return dt.toUTC().toFormat("yyyy-LL-dd'T'HH:mm:ss'Z'")
}

export function fmt(iso, tz) {
  return DateTime.fromISO(iso, { zone: 'utc' })
    .setZone(tz)
    .setLocale('ru')
    .toFormat('d LLL yyyy, HH:mm')
}

/** ISO со смещением из FullCalendar -> UTC с Z */
export function toUtcZ(isoWithOffset, tz) {
  return DateTime.fromISO(isoWithOffset, { zone: tz }).toUTC().toFormat("yyyy-LL-dd'T'HH:mm:ss'Z'")
}

export function nowIso() {
  return DateTime.utc().toFormat("yyyy-LL-dd'T'HH:mm:ss'Z'")
}

/** Ближайший час в поясе tz, для заметки по умолчанию */
export function nextHourLocal(tz) {
  const dt = DateTime.now().setZone(tz).plus({ hours: 1 }).startOf('hour')
  return dt.toFormat(LOCAL_FMT)
}

export function dateToLocalInput(dateStr, tz) {
  // dateStr вида 2026-11-05 -> 09:00 этого дня
  return `${dateStr.slice(0, 10)}T09:00`
}

export const TIMEZONES =
  typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : ['UTC']
