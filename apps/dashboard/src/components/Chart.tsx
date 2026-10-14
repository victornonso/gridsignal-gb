'use client';
import {useEffect,useRef} from 'react';
import * as echarts from 'echarts/core';
import {LineChart,BarChart,PieChart,HeatmapChart,MapChart} from 'echarts/charts';
import {GridComponent,TooltipComponent,LegendComponent,VisualMapComponent,GeoComponent,DataZoomComponent,AriaComponent} from 'echarts/components';
import {CanvasRenderer} from 'echarts/renderers';
import type {EChartsCoreOption} from 'echarts/core';
echarts.use([LineChart,BarChart,PieChart,HeatmapChart,MapChart,GridComponent,TooltipComponent,LegendComponent,VisualMapComponent,GeoComponent,DataZoomComponent,AriaComponent,CanvasRenderer]);
export default function Chart({option,label,onSelect}:{option:EChartsCoreOption;label:string;onSelect?:(value:string)=>void}){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!ref.current)return;const chart=echarts.init(ref.current,undefined,{renderer:'canvas'});
 chart.setOption({...option,animation:!matchMedia('(prefers-reduced-motion: reduce)').matches,animationDuration:300,aria:{enabled:true}});
 if(onSelect)chart.on('click',(event)=>onSelect(String(event.name)));
 const observer=new ResizeObserver(()=>chart.resize());observer.observe(ref.current);
 return()=>{observer.disconnect();chart.dispose()};},[option,onSelect]);
 return <div ref={ref} className="chart" role="img" aria-label={label}/>;
}
