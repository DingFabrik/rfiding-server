package utils

case class PaginatedResult[T](
  totalCount: Int,
  currentOffset: Int,
  entities: List[T], 
  hasNextPage: Boolean,
  pageSize: Int
)