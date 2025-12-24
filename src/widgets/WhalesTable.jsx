import React, { useEffect, useState } from "react";
import { getJSON } from "../lib/api.js";

export default function WhalesTable() {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    getJSON("/api/monitor/whales").then(d => setRows(d?.events || []));
  }, []);

  if (!rows.length) return <div>Aucun événement.</div>;

  return (
    <div style={{overflowX:"auto"}}>
      <table style={{width:"100%", borderCollapse:"collapse"}}>
        <thead>
          <tr>
            <th style={{textAlign:"left"}}>Token</th>
            <th>Type</th>
            <th>Amount</th>
            <th>Exchange</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((e, i) => (
            <tr key={i}>
              <td>{e.token}</td>
              <td style={{textAlign:"center"}}>{e.type}</td>
              <td style={{textAlign:"right"}}>{e.amount}</td>
              <td style={{textAlign:"center"}}>{e.exchange}</td>
              <td style={{textAlign:"center"}}>{e.ts}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
