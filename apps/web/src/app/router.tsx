import { createBrowserRouter } from 'react-router-dom'

import { RootLayout } from '@/app/layouts/RootLayout'
import { AdminPage } from '@/features/admin/AdminPage'
import { StallDetailPage } from '@/features/catalog/pages/StallDetailPage'
import { StallListPage } from '@/features/catalog/pages/StallListPage'
import { HomePage } from '@/features/home/HomePage'
import { MerchantPage } from '@/features/merchant/MerchantPage'
import { NotFoundPage } from '@/features/system/NotFoundPage'
import { RouteErrorPage } from '@/features/system/RouteErrorPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'stalls', element: <StallListPage /> },
      { path: 'stalls/:stallId', element: <StallDetailPage /> },
      { path: 'merchant', element: <MerchantPage /> },
      { path: 'admin', element: <AdminPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])