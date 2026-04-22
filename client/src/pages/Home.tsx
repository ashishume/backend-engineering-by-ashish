import { useEffect, useState } from "react";
import axios from "axios";

const useDebounce = (value: any, delay: any) => {
  const [debouncedVal, setDebounceVal] = useState(value);
  useEffect(() => {
    let timeout;
    return () => {
      timeout = setTimeout(() => {

      }, delay)
    }
  }, [])
}


function Home() {

  const [searchData, setSearchData] = useState<any>([])
  const [data,setData]=useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [totalPages, setTotalPages] = useState(0)
  const [page, setPage] = useState(1)

  const searchDataFunc = async (searchQuery: string) => {
    const response = await axios.get(`http://localhost:8000/search/?q=${searchQuery}&page=1&per_page=50`)
    return response?.data
  }

  
  useEffect(() => {
    if (searchTerm) {
      (async () => {
        const resp = await searchDataFunc(searchTerm)
        setData(resp.results)
        setSearchData(resp.results)
        paginatedData(resp.results)
        setTotalPages(resp.pagination.total)
      })()
    }

  }, [searchTerm])


  const handleSearch = (e: any) => {
    const val = e.target.value
    setSearchTerm(val)
  }

  const handlePrev = (e: any) => {
    // if (page > 0) {
      setPage(prev => prev - 1)
    // }
  }

  const handleNext = (e: any) => {
    // if (page <= totalPages) {
      setPage(prev => prev + 1)
    // }
  }

  const paginatedData=(data:any[])=>{
    const startIndex = (page - 1) * 5;
    const endIndex = startIndex + 5;
    const paginatedData = data.slice(startIndex, endIndex);
  }

  return (
    <div style={{
      maxWidth:"750px",
      backgroundColor:"#f2f2f2",
      padding:"10px",
      margin:"0 auto"
    }}>
      <div style={{
        backgroundColor:"#fff"
      }}>
        <input placeholder="search" onChange={handleSearch} style={{
          width:"100%"
        }} />
      </div>
      <table width={"100%"} style={{
        padding:"10px"
      }}>
        <thead>
          <tr>
            <td>Name</td>
            <td>City</td>
          </tr>
        </thead>
        <tbody style={{
          border:"solid 1px black",
          padding:"10px"
        }}>
          {
            searchData.map((value: any, i: any) => {
              return <tr key={i} style={{
                padding:"10px",
                      border:"solid 1px black"
              }}>
                <td style={{
                  padding:"2px 5px",
                }}>{value.name}</td>
                <td style={{
                  padding:"2px 5px",
                }}>{value.city}</td>
              </tr>
            })
          }

        </tbody>
      </table>

      <div style={{
        display: "flex",
        justifyContent: "space-between",
        backgroundColor: "skyblue"
      }}>
        <div onClick={handlePrev}>Left</div>
        <div onClick={handleNext}>Right</div>
      </div>
    </div>
  );
}

export default Home;
