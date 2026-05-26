import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
    'X-Analyst-Email': 'analyst@breatheesg.com' // Mandatory audit lineage signature
  }
})
