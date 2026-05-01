// offlineQueue.js

const DB_NAME = 'KrishiDB';
const DB_VERSION = 1;
const STORE_NAME = 'requests';

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = (event) => reject('IndexedDB error: ' + event.target.error);
    
    request.onsuccess = (event) => resolve(event.target.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

export async function saveToQueue(url, formData) {
  const db = await openDB();
  
  // Convert FormData to an object we can store (IndexedDB supports Files/Blobs)
  const payloadData = {};
  for (let [key, value] of formData.entries()) {
    payloadData[key] = value;
  }

  const payload = {
    url,
    timestamp: Date.now(),
    data: payloadData
  };

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.add(payload);
    
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function flushQueue() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();
    
    request.onsuccess = async () => {
      const requests = request.result;
      for (const req of requests) {
        try {
          // Attempt to send (re-construct FormData)
          console.log("Flushing request to:", req.url);
          const fd = new FormData();
          for (const key in req.data) {
            fd.append(key, req.data[key]);
          }
          
          const response = await fetch(req.url, { method: 'POST', body: fd });
          if (!response.ok) throw new Error("Server rejected flush sync");
          
          // If successful, delete from queue
          const delTx = db.transaction(STORE_NAME, 'readwrite');
          delTx.objectStore(STORE_NAME).delete(req.id);
        } catch (e) {
          console.error("Failed to sync offline request", e);
          break; // Stop on first failure to maintain order
        }
      }
      resolve();
    };
    request.onerror = () => reject(request.error);
  });
}
