const apiOrigin = process.env.HPS_LOCAL_API;

export default {
  poweredByHeader: false,
  ...(apiOrigin ? {
    async rewrites() {
      return [{ source: "/api/:path*", destination: apiOrigin + "/api/:path*" }];
    },
  } : { output: "export" }),
};
