import { createBrowserRouter } from 'react-router-dom'

import { RootLayout } from '@/app/layouts/RootLayout'
import { AdminPage } from '@/features/admin/AdminPage'
import { HomePage } from '@/features/home/HomePage'
import { MerchantPage } from '@/features/merchant/MerchantPage'
import { NotFoundPage } from '@/features/system/NotFoundPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'merchant', element: <MerchantPage /> },
      { path: 'admin', element: <AdminPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])