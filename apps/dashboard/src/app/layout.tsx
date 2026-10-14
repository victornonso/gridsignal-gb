import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'GridSignal — Great Britain electricity intelligence',description:'Explore carbon intensity, generation, demand and the quality of Great Britain electricity data.'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
