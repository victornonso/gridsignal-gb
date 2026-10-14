import {Suspense} from 'react';
import {Dashboard} from '@/components/Dashboard';
export default function Page(){return <Suspense fallback={<main className="boot">Connecting to GridSignal…</main>}><Dashboard/></Suspense>}
