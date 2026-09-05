# Static deployment

Build the frontend with `npm run build` and publish `dist`.

The build copies `public/_redirects` into `dist/_redirects`, enabling SPA
fallback for Netlify-compatible static hosts. On other hosts, configure every
unmatched route to serve `index.html` so React Router can handle
`/transactions`, `/intelligence`, `/simulation`, and `/settings`.

Set `VITE_API_URL` to the public HTTPS URL of the backend before building.
