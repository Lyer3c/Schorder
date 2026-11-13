import { createBrowserRouter } from 'react-router-dom'

import { RootLayout } from '@/app/layouts/RootLayout'
import { AdminPage } from '@/features/admin/AdminPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { RequireAuth } from '@/features/auth/RequireAuth'
import { CartPage } from '@/features/cart/CartPage'
import { StallDetailPage } from '@/features/catalog/pages/StallDetailPage'
import { StallListPage } from '@/features/catalog/pages/StallListPage'
import { CheckoutPage } from '@/features/checkout/CheckoutPage'
import { HomePage } from '@/features/home/HomePage'
import { MerchantPage } from '@/features/merchant/MerchantPage'
import { OrderDetailPage } from '@/features/orders/OrderDetailPage'
import { OrdersPage } from '@/features/orders/OrdersPage'
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
      { path: 'login', element: <LoginPage /> },
      { path: 'cart', element: <CartPage /> },
      {
        path: 'checkout',
        element: (
          <RequireAuth>
            <CheckoutPage />
          </RequireAuth>
        ),
      },
      {
        path: 'orders',
        element: (
          <RequireAuth>
            <OrdersPage />
          </RequireAuth>
        ),
      },
      {
        path: 'orders/:orderId',
        element: (
          <RequireAuth>
            <OrderDetailPage />
          </RequireAuth>
        ),
      },
      { path: 'merchant', element: <MerchantPage /> },
      { path: 'admin', element: <AdminPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])