import { createApp, analytics, files, genie, server } from '@databricks/appkit';

const genieSpaceId = process.env.DATABRICKS_GENIE_SPACE_ID ?? '';

createApp({
  plugins: [
    analytics(),
    files({
      volumes: {
        files: {
          maxUploadSize: 50 * 1024 * 1024,
          policy: files.policy.allowAll(),
        },
      },
    }),
    genie({
      spaces: {
        default: genieSpaceId,
      },
    }),
    server(),
  ],
  onPluginsReady(appkit) {
    appkit.server.extend((app) => {
      app.get('/api/whoami', (req, res) => {
        const email = req.header('x-forwarded-email') ?? null;
        const user = req.header('x-forwarded-user') ?? null;
        res.json({
          email,
          user,
          executionMode: 'obo',
          genieSpaceConfigured: Boolean(genieSpaceId),
        });
      });
    });
  },
}).catch(console.error);
