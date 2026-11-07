import { useEffect, useState } from "react";

export default function App() {
    const [products, setProducts] = useState([]);

    useEffect(() => {
        fetch("/api/products")
            .then((res) => res.json())
            .then(setProducts);
    }, []);

    return (
        <main>
            <h1>商品一覧（watch）</h1>
            <ul>
                {products.map((p) => (
                    <li key={p.id}>
                        {p.name} — {p.price}円
                    </li>
                ))}
            </ul>
        </main>
    );
}
