import { MongoClient } from 'mongodb';

const uri = process.env.MONGODB_URI!;

let clientPromise: Promise<MongoClient>;

declare global {
  // eslint-disable-next-line no-var
  var _mongoClientPromise: Promise<MongoClient> | undefined;
}

const options = {
  serverSelectionTimeoutMS: 5000, // fail fast instead of waiting 30s
  connectTimeoutMS: 5000,
};

if (process.env.NODE_ENV === 'development') {
  // Reuse connection across HMR reloads in dev
  if (!global._mongoClientPromise) {
    const client = new MongoClient(uri, options);
    global._mongoClientPromise = client.connect();
  }
  clientPromise = global._mongoClientPromise;
} else {
  const client = new MongoClient(uri, options);
  clientPromise = client.connect();
}

export default clientPromise;
