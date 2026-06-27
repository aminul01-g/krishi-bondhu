/**
 * IndexedDB-backed offline queue for Emergency damage reports.
 *
 * During disasters (flood, cyclone) connectivity fails. Damage reports queued
 * here survive page reloads and are replayed automatically once the device is
 * back online (see hooks/useEmergencyQueue.js).
 *
 * Two object stores live in the `krishibondhu` database:
 *
 *   - `emergency_queue` : one record per pending report. Lightweight — holds
 *     only text/numbers plus a `photoIds[]` list. keyPath: `id`.
 *   - `photos`          : raw photo Blobs, stored separately so the queue
 *     stays small and photo bytes are only read back at submit time. Blobs are
 *     stored natively (NOT base64) which is storage-efficient in IndexedDB.
 *     keyPath: `id`.
 *
 * A queued report has the shape:
 *   { id, timestamp, cropType, damageCause, damagePercent, voiceText,
 *     lat, lon, status: 'pending', photoIds: [id, ...] }
 */

import { openDB } from 'idb';

const DB_NAME = 'krishibondhu';
const DB_VERSION = 1;
const QUEUE_STORE = 'emergency_queue';
const PHOTOS_STORE = 'photos';

let dbPromise;

/** Lazily open (and upgrade) the database. Shared across callers. */
function getDb() {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(QUEUE_STORE)) {
          db.createObjectStore(QUEUE_STORE, { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains(PHOTOS_STORE)) {
          db.createObjectStore(PHOTOS_STORE, { keyPath: 'id' });
        }
      },
    });
  }
  return dbPromise;
}

/** Generate a unique id, preferring the native UUID primitive. */
function uuid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for very old browsers / insecure contexts.
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Persist a damage report (and its photos) for later retry.
 *
 * @param {Object} report  Report fields (cropType, damageCause, etc.).
 *                         `id`/`timestamp`/`status` are filled in if absent.
 * @param {File[]} [photoFiles]  Original photo files; stored as native Blobs.
 * @returns {Promise<Object>} the stored report (with its `id`).
 */
export async function queueReport(report, photoFiles = []) {
  const db = await getDb();
  const tx = db.transaction([QUEUE_STORE, PHOTOS_STORE], 'readwrite');

  // Store each photo Blob in the dedicated store and collect references.
  const photoIds = [];
  for (const file of photoFiles) {
    const photoId = uuid();
    await tx.objectStore(PHOTOS_STORE).put({
      id: photoId,
      // Wrap the File in a plain Blob so IndexedDB persists the bytes; keep
      // metadata so we can reconstruct a File on retry (name/type matter for
      // multipart uploads).
      blob: new Blob([file], { type: file.type || 'image/jpeg' }),
      name: file.name || `photo-${photoId}.jpg`,
      type: file.type || 'image/jpeg',
      size: file.size,
    });
    photoIds.push(photoId);
  }

  const record = {
    id: uuid(),
    timestamp: Date.now(),
    status: 'pending',
    photoIds,
    ...report,
  };
  await tx.objectStore(QUEUE_STORE).put(record);
  await tx.done;
  return record;
}

/** Return all pending reports, oldest first. */
export async function getPendingReports() {
  const db = await getDb();
  const all = await db.getAll(QUEUE_STORE);
  return all
    .filter((r) => r && r.status === 'pending')
    .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
}

/** Number of pending reports (for the nav badge). */
export async function getPendingCount() {
  const db = await getDb();
  const all = await db.getAll(QUEUE_STORE);
  return all.filter((r) => r && r.status === 'pending').length;
}

/**
 * Reconstruct the original File objects for a report's stored photos.
 * @param {string[]} photoIds
 * @returns {Promise<File[]>}
 */
export async function getPhotos(photoIds = []) {
  if (!photoIds.length) return [];
  const db = await getDb();
  const files = [];
  for (const id of photoIds) {
    const rec = await db.get(PHOTOS_STORE, id);
    if (rec && rec.blob) {
      files.push(new File([rec.blob], rec.name || 'photo.jpg', { type: rec.type }));
    }
  }
  return files;
}

/**
 * Delete a report and its associated photo records.
 * @param {string} id  report id
 */
export async function removeReport(id) {
  const db = await getDb();
  const report = await db.get(QUEUE_STORE, id);
  const tx = db.transaction([QUEUE_STORE, PHOTOS_STORE], 'readwrite');
  if (report && Array.isArray(report.photoIds)) {
    for (const pid of report.photoIds) {
      await tx.objectStore(PHOTOS_STORE).delete(pid);
    }
  }
  await tx.objectStore(QUEUE_STORE).delete(id);
  await tx.done;
}
