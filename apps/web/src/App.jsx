import { useEffect, useState } from "react";

// カートの ID をブラウザに保存し、次に開いたときも同じカートを使う
function getCartId() {
    let id = localStorage.getItem("cartId");
    if (!id) {
        id = crypto.randomUUID();
        localStorage.setItem("cartId", id);
    }
    return id;
}

const headers = {
    "X-Cart-Id": getCartId(),
    "Content-Type": "application/json",
};

export default function App() {
    const [products, setProducts] = useState([]);
    const [cart, setCart] = useState({});

    useEffect(() => {
        fetch("/api/products")
            .then((res) => res.json())
            .then(setProducts);
        fetch("/api/cart", { headers })
            .then((res) => res.json())
            .then((data) => setCart(data.items));
    }, []);

    function addToCart(productId) {
        fetch("/api/cart/items", {
            method: "POST",
            headers,
            body: JSON.stringify({ product_id: productId }),
        })
            .then((res) => res.json())
            .then((data) => setCart(data.items));
    }

    const count = Object.values(cart).reduce((sum, n) => sum + n, 0);

    return (
        <main>
            <h1>商品一覧</h1>
            <p>カート: {count} 点</p>
            <ul>
                {products.map((p) => (
                    <li key={p.id}>
                        {p.thumbnail_url && (
                            <img src={p.thumbnail_url} alt="" />
                        )}
                        {p.name} — {p.price}円
                        <button onClick={() => addToCart(p.id)}>
                            カートに入れる
                        </button>
                    </li>
                ))}
            </ul>
        </main>
    );
}
