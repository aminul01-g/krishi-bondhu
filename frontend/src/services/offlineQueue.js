// offlineQueue.js - Advanced Resilience Layer

const DB_NAME = 'KrishiDB';
const DB_VERSION = 2; // Incremented version for status and attempt fields
const STORE_NAME = 'requests';

/**
 * Opens IndexedDB and handles upgrades.
 */
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = (event) => reject('IndexedDB error: ' + event.target.error);
    request.onsuccess = (event) => resolve(event.target.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      } else {
        // Upgrade logic if needed for existing stores
        // We ensure indices for status to quickly find pending items
        const store = event.currentTarget.transaction.objectStore(STORE_NAME);
        if (!store.indexNames.contains('status')) {
          store.createIndex('status', 'status', { unique: false });
        }
      }
    };
  });
}

/**
 * Saves a request to the queue.
 */
export async function saveToQueue(url, data, type = 'JSON') {
  const db = await openDB();
  
  let payloadData = data;
  if (data instanceof FormData) {
    payloadData = {};
    for (let [key, value] of data.entries()) {
      payloadData[key] = value;
    }
  }

  const payload = {
    url,
    timestamp: Date.now(),
    data: payloadData,
    type,
    status: 'pending',
    attempts: 0,
    lastError: null,
    last_updated_at: new Date().toISOString() // Conflict resolution timestamp
  };

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.add(payload);
    
    request.onsuccess = () => {
      resolve(request.result);
      window.dispatchEvent(new CustomEvent('offline-sync-updated', { detail: { count: 'update' } }));
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Flushes all pending requests with retry logic and status tracking.
 */
export async function flushQueue() {
  if (!navigator.onLine) return;

  const db = await openDB();
  const tx = db.transaction(STORE_NAME, 'readwrite');
  const store = tx.objectStore(STORE_NAME);
  const request = store.getAll();
  
  return new Promise((resolve, reject) => {
    request.onsuccess = async () => {
      const requests = request.result.filter(r => r.status !== 'syncing');
      
      for (const req of requests) {
        try {
          // Mark as syncing to avoid double-sends
          req.status = 'syncing';
          req.attempts += 1;
          
          const updateTx = db.transaction(STORE_NAME, 'readwrite');
          updateTx.objectStore(STORE_NAME).put(req);

          let response;
          if (req.type === 'FormData') {
            const fd = new FormData();
            for (const key in req.data) fd.append(key, req.data[key]);
            response = await fetch(req.url, { method: 'POST', body: fd });
          } else {
            response = await fetch(req.url, { 
              method: 'POST', 
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(req.data) 
            });
          }

          if (!response.ok) throw new Error(`Server status: ${response.status}`);
          
          // Success: Delete from queue
          const delTx = db.transaction(STORE_NAME, 'readwrite');
          delTx.objectStore(STORE_NAME).delete(req.id);
          console.log(`✅ Synced: ${req.url}`);

        } catch (e) {
          console.error(`❌ Sync Failed (${req.attempts}/5): ${req.url}`, e);
          
          req.status = req.attempts >= 5 ? 'failed' : 'pending';
          req.lastError = e.message;
          
          const failTx = db.transaction(STORE_NAME, 'readwrite');
          failTx.objectStore(STORE_NAME).put(req);
          
          // If network is gone, stop trying
          if (!navigator.onLine) break;
        }
      }
      
      window.dispatchEvent(new CustomEvent('offline-sync-updated', { detail: { finished: true } }));
      resolve();
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Helper to get the count of pending items.
 */
export async function getQueueCount() {
  const db = await openDB();
  return new Promise((resolve) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.count();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(0);
  });
}
