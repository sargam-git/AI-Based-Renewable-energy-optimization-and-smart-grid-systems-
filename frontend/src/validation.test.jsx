import { describe,it,expect,vi } from 'vitest';
import { render,screen,fireEvent } from '@testing-library/react';
import { number,money,hour,downloadCSV } from './services/api';
import { Badge,Card,Stat,DataTable,BatteryGauge,Progress } from './components/UI';
import GridTopology from './components/GridTopology';
describe('formatting and CSV utilities',()=>{
 it('formats finite numbers and missing values',()=>{expect(number(1234.567,1)).toBe('1,234.6');expect(number(null)).toBe('—');expect(money(12.5)).toBe('$12.50');});
 it('exports CSV through an object URL',()=>{globalThis.URL.createObjectURL=vi.fn(()=> 'blob:test');globalThis.URL.revokeObjectURL=vi.fn();const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});downloadCSV('a,b\n1,2','test.csv');expect(click).toHaveBeenCalled();expect(URL.createObjectURL).toHaveBeenCalled();click.mockRestore();});
});
describe('accessible reusable interface',()=>{
 it('renders card and status',()=>{render(<Card title='Energy'><Badge>Balanced</Badge></Card>);expect(screen.getByText('Energy')).toBeInTheDocument();expect(screen.getByText('Balanced')).toBeInTheDocument();});
 it('renders live metrics and units',()=>{render(<Stat label='Demand' value='400' unit='kW' detail='Current hour'/>);expect(screen.getByText('Demand')).toBeInTheDocument();expect(screen.getByText('kW')).toBeInTheDocument();});
 it('renders tabular data',()=>{render(<DataTable columns={[{key:'name',label:'Asset'}]} rows={[{name:'Transformer'}]}/>);expect(screen.getByText('Transformer')).toBeInTheDocument();});
 it('renders battery state accessibly',()=>{render(<BatteryGauge soc={62} energy={744} capacity={1200} status='Idle'/>);expect(screen.getByRole('img',{name:/62.*percent/})).toBeInTheDocument();});
 it('clamps progress visually',()=>{const {container}=render(<Progress value={120}/>);expect(container.querySelector('.progress span').style.width).toBe('100%');});
});
describe('backend-driven grid topology',()=>{
 it('shows actual supplied flow values and changes selected node',()=>{const current={solar_predicted_kw:350,wind_predicted_kw:150,discharge_kw:0,charge_kw:40,import_kw:0,export_kw:60,residential_kw:150,commercial_kw:100,industrial_kw:150,residential_served_kw:150,commercial_served_kw:100,industrial_served_kw:150,served_kw:400,demand_predicted_kw:400,unserved_kw:0};render(<GridTopology current={current} config={{battery:{capacity_kwh:1200},grid_available:true}}/>);fireEvent.click(screen.getByRole('button',{name:'Inspect Solar array'}));expect(screen.getAllByText('350.0 kW').length).toBeGreaterThan(0);expect(screen.getByRole('button',{name:'Inspect Battery storage'}).textContent).toContain('40.0');});
});
